import pkgutil
import os
import json
import yaml
import boto3
from typing import Union
from pulumi import ComponentResource, Config

# from pulumi_aws import get_caller_identity, get_region

import cloud_foundry

from api_foundry.iac.gateway_spec import APISpecEditor
from api_foundry.utils.model_factory import ModelFactory
from cloud_foundry import logger

log = logger(__name__)


def is_valid_openapi_spec(spec_dict: dict) -> bool:
    return (
        isinstance(spec_dict, dict)
        and "openapi" in spec_dict
        and isinstance(spec_dict["openapi"], str)
    )


def load_api_spec(api_spec: Union[str, list[str]]) -> dict:
    api_spec_dict = {}
    specs = [api_spec] if isinstance(api_spec, str) else api_spec

    all_specs = []
    for spec in specs:
        if os.path.isfile(spec):
            all_specs.append(spec)
        elif os.path.isdir(spec):
            all_specs.extend(
                sorted(
                    [
                        os.path.join(spec, f)
                        for f in os.listdir(spec)
                        if f.endswith(".yaml")
                    ]
                )
            )
        elif spec.startswith("s3://"):
            s3 = boto3.client("s3")
            bucket, key = spec[5:].split("/", 1)
            if key.endswith("/"):
                response = s3.list_objects_v2(Bucket=bucket, Prefix=key)
                all_specs.extend(
                    sorted(
                        [
                            f"s3://{bucket}/{obj['Key']}"
                            for obj in response.get("Contents", [])
                            if obj["Key"].endswith(".yaml")
                        ]
                    )
                )
            else:
                all_specs.append(spec)
        else:
            try:
                spec_dict = yaml.safe_load(spec)
                if is_valid_openapi_spec(spec_dict):
                    api_spec_dict.update(spec_dict)
                    return api_spec_dict
            except yaml.YAMLError:
                raise ValueError(f"Invalid OpenAPI spec provided: {spec}")

    for spec in all_specs:
        if spec.startswith("s3://"):
            bucket, key = spec[5:].split("/", 1)
            s3 = boto3.client("s3")
            obj = s3.get_object(Bucket=bucket, Key=key)
            spec_dict = yaml.safe_load(obj["Body"].read().decode("utf-8"))
        else:
            with open(spec, "r") as yaml_file:
                spec_dict = yaml.safe_load(yaml_file)

        if not is_valid_openapi_spec(spec_dict):
            raise ValueError(f"Invalid OpenAPI spec found in: {spec}")

        api_spec_dict.update(spec_dict)

    return api_spec_dict


class APIFoundry(ComponentResource):
    api_spec_editor: APISpecEditor

    def __init__(
        self,
        name,
        *,
        api_spec: Union[str, list[str]],
        secrets: str,
        environment: dict[str, str] = {},
        body: Union[str, list[str]] = [],
        integrations: list[dict] = [],
        token_validators: list[dict] = [],
        policy_statements: list = [],
        vpc_config: dict = {},
        opts=None,
    ):
        super().__init__("cloud_foundry:apigw:APIFoundry", name, None, opts)

        api_spec_dict = load_api_spec(api_spec)

        if isinstance(body, str):
            body = [body]

        # Check if we are deploying to LocalStack
        if self.is_deploying_to_localstack():
            # Add LocalStack-specific environment variables
            localstack_env = {
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_ENDPOINT_URL": "http://localstack:4566",
            }
            environment = {**localstack_env, **environment}
        environment["SECRETS"] = secrets

        #        account_id = get_caller_identity().account_id
        #        region = get_region().name
        for database, secret_name in json.loads(secrets).items():
            policy_statements.append(
                {
                    "Effect": "Allow",
                    "Actions": ["secretsmanager:GetSecretValue"],
                    "Resources": ["*"],
                    # "Resources": [f"arn:aws:secretsmanager:{region}:{account_id}:secret:{secret_name}"],
                }
            )

        self.api_function = cloud_foundry.python_function(
            name=name,
            environment=environment,
            sources={
                "api_spec.yaml": yaml.safe_dump(
                    ModelFactory(api_spec_dict).get_config_output()
                ),
                "app.py": pkgutil.get_data(
                    "api_foundry_query_engine", "lambda_handler.py"
                ).decode(),  # type: ignore
            },
            requirements=["psycopg2-binary", "pyyaml", "api_foundry_query_engine"],
            policy_statements=policy_statements,
            vpc_config=vpc_config,
        )

        gateway_spec = APISpecEditor(
            open_api_spec=api_spec_dict,
            function=self.api_function,
            function_name=name,
        )
        #        log.info(f"integrations: {gateway_spec.integrations}")
        self.rest_api = cloud_foundry.rest_api(
            name,
            body=[*body, gateway_spec.rest_api_spec()],
            integrations=[*integrations, *gateway_spec.integrations],
            token_validators=token_validators,
        )

    def integrations(self) -> list[dict]:
        return self.api_spec_editor.integrations

    def is_deploying_to_localstack(self) -> bool:
        # Create a Pulumi Config instance
        config = Config("aws")

        # Check if the 'endpoints' configuration is set, which usually indicates LocalStack
        endpoints = config.get("endpoints")

        if endpoints:
            try:
                # Parse the endpoints configuration and check for LocalStack URL
                endpoints_list = json.loads(endpoints)
                for endpoint in endpoints_list:
                    if "localhost" in endpoint.get("url", ""):
                        return True
            except json.JSONDecodeError:
                pass

        return False

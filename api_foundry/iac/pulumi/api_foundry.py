import os
import json
import yaml
import boto3
from typing import Optional, Union
from pulumi import ComponentResource, Config

import pulumi
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
        secrets: Optional[str] = None,
        environment: Optional[dict[str, Union[str, pulumi.Output[str]]]] = None,
        integrations: Optional[list[dict]] = None,
        token_validators: Optional[list[dict]] = None,
        policy_statements: Optional[list] = None,
        vpc_config: Optional[dict] = None,
        export_api: Optional[str] = None,
        opts=None,
    ):
        super().__init__("cloud_foundry:apigw:APIFoundry", name, None, opts)

        api_spec_dict = load_api_spec(api_spec)
        config_defaults = api_spec_dict.get("x-af-configuration", {})

        secrets = secrets or config_defaults.get("secrets", "")
        env_vars = environment or config_defaults.get(
            "environment", {}
        )  # type: dict[str, Union[str, pulumi.Output[str]]]
        integrations = integrations or config_defaults.get("integrations", [])
        token_validators = token_validators or config_defaults.get(
            "token_validators", []
        )
        policy_statements = policy_statements or config_defaults.get(
            "policy_statements", []
        )
        vpc_config = vpc_config or config_defaults.get("vpc_config", {})

        # Check if we are deploying to LocalStack
        if self.is_deploying_to_localstack():
            # Add LocalStack-specific environment variables
            localstack_env = {
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_ENDPOINT_URL": "http://localstack:4566",
            }
            env_vars = {**localstack_env, **env_vars}
        env_vars["SECRETS"] = secrets

        for database, secret_name in json.loads(secrets).items():
            policy_statements.append(
                {
                    "Effect": "Allow",
                    "Actions": ["secretsmanager:GetSecretValue"],
                    "Resources": ["*"],
                }
            )

        self.api_function = cloud_foundry.python_function(
            name=name,
            environment=env_vars,
            handler="api_foundry_query_engine.lambda_handler.handler",
            sources={
                "api_spec.yaml": yaml.safe_dump(
                    ModelFactory(api_spec_dict).get_config_output()
                ),
            },
            requirements=["psycopg2-binary", "pyyaml", "api_foundry_query_engine"],
            policy_statements=policy_statements,
            vpc_config=vpc_config,
        )

        gateway_spec = APISpecEditor(
            open_api_spec=api_spec_dict, function=self.api_function
        )

        self.rest_api = cloud_foundry.rest_api(
            name,
            specification=[gateway_spec.rest_api_spec()],
            integrations=gateway_spec.integrations,
            token_validators=token_validators or [],
            export_api=export_api,
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.domain = self.rest_api.domain

        self.register_outputs({f"{name}_domain": self.domain})

    def integrations(self) -> list[dict]:
        return self.api_spec_editor.integrations

    def is_deploying_to_localstack(self) -> bool:
        config = Config("aws")
        endpoints = config.get("endpoints")

        if endpoints:
            try:
                endpoints_list = json.loads(endpoints)
                for endpoint in endpoints_list:
                    if "localhost" in endpoint.get("url", ""):
                        return True
            except json.JSONDecodeError:
                pass

        return False

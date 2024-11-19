import pkgutil
import os
import json
import yaml
from typing import Union
from pulumi import ComponentResource, Config

import cloud_foundry

from api_foundry.iac.gateway_spec import APISpecEditor
from api_foundry.utils.model_factory import ModelFactory
from api_foundry.utils.logger import logger

log = logger(__name__)


class APIFoundry(ComponentResource):
    api_spec_editor: APISpecEditor

    def __init__(
        self,
        name,
        *,
        api_spec: str,
        secrets: str,
        environment: dict[str, str] = {},
        body: Union[str, list[str]] = [],
        integrations: list[dict] = [],
        token_validators: list[dict] = [],
        policy_statements: list = [],
        opts=None,
    ):
        super().__init__("cloud_foundry:apigw:APIFoundry", name, None, opts)

        if os.path.exists(api_spec):
            with open(api_spec, "r") as yaml_file:
                api_spec_dict = yaml.safe_load(yaml_file)
        else:
            api_spec_dict = yaml.safe_load(api_spec)

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

        self.api_function = cloud_foundry.python_function(
            name=name,
            environment=environment,
            sources={
                "api_spec.yaml": yaml.safe_dump(
                    ModelFactory(api_spec_dict).get_config_output()
                ),
                "app.py": pkgutil.get_data(
                    "api_foundry_query_engine", "lambda_handler.py"
                ).decode(
                    "utf-8"
                ),  # type: ignore
            },
            requirements=["psycopg2-binary", "pyyaml", "api_foundry_query_engine"],
            policy_statements=policy_statements,
        )

        gateway_spec = APISpecEditor(
            open_api_spec=api_spec_dict,
            function=self.api_function,
            function_name=name,
        )
        #        log.info(f"integrations: {gateway_spec.integrations}")
        self.rest_api = cloud_foundry.rest_api(
            f"{name}-rest-api",
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

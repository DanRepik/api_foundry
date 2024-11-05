import pkgutil
import json
import importlib.resources as pkg_resources
from pathlib import Path
from pulumi import ComponentResource, Output, ResourceOptions, export, Config
import pulumi_aws as aws
from typing import Any, Awaitable, Mapping, Dict

import cloud_foundry

from api_foundry.iac.gateway_spec import APISpecEditor
from api_foundry.utils.logger import logger, DEBUG, write_logging_file
from api_foundry.utils.model_factory import ModelFactory

log = logger(__name__)


class APIFoundry(cloud_foundry.RestAPI):
    def __init__(
        self,
        name,
        body: Union[str, list[str]],
        integrations: list[dict] = None,
        authorizers: list[dict] = None,
        opts=None,
    ):
        super().__init__("cloud_forge:apigw:RestAPI", name, None, opts)

        api_spec = str(props.get("api_spec", None))
        assert api_spec, "api_spec is not set, a location must be provided."
        assert "secrets" in props, "Missing secrets map"

        # Dynamically obtain the path to the `api_foundry` package
        with pkg_resources.path("api_foundry", "__init__.py") as p:
            api_foundry_source = str(Path(p).parent)

        environment = props.get("environment") if isinstance(props.get("environment"), dict) else {}         # type: ignore
        # Check if we are deploying to LocalStack
        if self.is_deploying_to_localstack():
            # Add LocalStack-specific environment variables
            localstack_env = {
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_ENDPOINT_URL": "http://localstack:4566",
            }
            environment = {**localstack_env, **environment}

        environment['secrets'] = props["secrets"]

        lambda_function = cloud_foundry.python_function(
            name=f"{name}-api-maker",
            sources={
                "api_foundry": api_foundry_source,
                "api_spec.yaml": api_spec,
                "app.py": pkgutil.get_data("api_foundry", "iac/handler.py").decode("utf-8"),  # type: ignore
            },
            requirements=[
                "psycopg2-binary",
                "pyyaml",
            ],
            environment=environment
        )


        ModelFactory.load_yaml(api_spec)

        body = lambda_function.invoke_arn().apply(
            lambda invoke_arn: (
                APISpecEditor(
                    function_name=lambda_function.name,
                    function_invoke_arn=invoke_arn,
                    enable_cors=True,
                ).as_yaml()
            )
        )

        rest_api = cloud_foundry.rest_api(
            f"{name}-http-api",
            body=body,
            integrations=
        )

        export("gateway-api", rest_api.id)

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

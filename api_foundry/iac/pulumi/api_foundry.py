import pkgutil
import pulumi
import json
import yaml
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
        api_spec,
        opts=None,
    ):
        super().__init__("cloud_forge:apigw:RestAPI", name, None, opts)
        self.name = name
        self.api_spec = api_spec
        self.function_name = f"{self.name}-api-foundry"

        model_factory = ModelFactory()
        model_factory.set_spec(yaml.safe_load(api_spec))

        self.function = cloud_foundry.python_function(
            name=self.function_name,
            sources={
                "api_spec.yaml": yaml.safe_dump(model_factory.get_config_output()),
                "app.py": pkgutil.get_data("api_foundry_query_engine", "lambda_handler.py").decode("utf-8"),  # type: ignore
            },
            requirements=["psycopg2-binary", "pyyaml", "api_foundry_query_engine"],
        )

        rest_api_spec = APISpecEditor()
        self.rest_api = cloud_foundry.rest_api(
            f"{self.name}-rest-api",
            body="./api_spec.yaml",
            integrations=model_factory.get_integrations()
            #            [{"path": "/greet", "method": "get", "function": greet_function}],
        )

        def build(function: cloud_foundry.Function):
            self.api_spec_editor = APISpecEditor(
                function_name=self.function_name, function=function
            )
            log.info("returning from build")
            return pulumi.Output.from_input(None)

        self.api_function.invoke_arn.apply(lambda invoke_arn: (build(self.function)))

        """
        environment = props.get("environment") if isinstance(props.get("environment"), dict) else {} 
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
        """

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

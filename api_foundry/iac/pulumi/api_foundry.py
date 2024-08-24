import pkgutil
import importlib.resources as pkg_resources
from pathlib import Path
from pulumi import ComponentResource, Output, ResourceOptions, export
import pulumi_aws as aws
from typing import Any, Awaitable, Mapping

from api_foundry.iac.gateway_spec import GatewaySpec
from api_foundry.cloudprints.python_archive_builder import PythonArchiveBuilder
from api_foundry.cloudprints.pulumi.lambda_ import PythonFunctionCloudprint
from api_foundry.utils.logger import logger, DEBUG, write_logging_file
from api_foundry.utils.model_factory import ModelFactory

log = logger(__name__)


class APIFoundry(ComponentResource):
    def __init__(
        self,
        name: str,
        props: Mapping[str, Any | Awaitable[Any] | Output[Any]],
        opts: ResourceOptions | None = None,
        remote: bool = False,
    ) -> None:
        super().__init__("api_foundry", name, props, opts, remote)

        api_spec = str(props.get("api_spec", None))
        assert api_spec, "api_spec is not set, a location must be provided."
        assert "secrets" in props, "Missing secrets map"

        # Dynamically obtain the path to the `api_foundry` package
        with pkg_resources.path("api_foundry", "__init__.py") as p:
            api_foundry_source = str(Path(p).parent)

        self.archive_builder = PythonArchiveBuilder(
            name=f"{name}-archive-builder",
            sources={
                "api_foundry": api_foundry_source,
                "api_spec.yaml": api_spec,
                "app.py": pkgutil.get_data("api_foundry", "iac/handler.py").decode("utf-8"),  # type: ignore
            },
            requirements=[
                "psycopg2-binary",
                "pyyaml",
            ],
            working_dir="temp",
        )

        lambda_function = PythonFunctionCloudprint(
            name=f"{name}-api-maker",
            hash=self.archive_builder.hash(),
            handler="app.lambda_handler",
            archive_location=self.archive_builder.location(),
            environment={
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_ENDPOINT_URL": "http://localstack:4566",
                "SECRETS": props["secrets"],
            },
        )

        ModelFactory.load_yaml(api_spec)

        body = lambda_function.invoke_arn().apply(
            lambda invoke_arn: (
                GatewaySpec(
                    function_name=lambda_function.name,
                    function_invoke_arn=invoke_arn,
                    enable_cors=True,
                ).as_yaml()
            )
        )

        if log.isEnabledFor(DEBUG):
            body.apply(
                lambda body_str: (
                    write_logging_file(f"{name}-gateway-doc.yaml", body_str)
                )
            )

        gateway = aws.apigateway.RestApi(
            f"{name}-http-api",
            name=f"{name}-http-api",
            body=body,
        )

        deployment = aws.apigateway.Deployment(
            f"{name}-deployment", rest_api=gateway.id
        )

        aws.apigateway.Stage(
            f"{name}-stage",
            rest_api=gateway.id,
            deployment=deployment.id,
            stage_name=name,
        )

        export("gateway-api", gateway.id)

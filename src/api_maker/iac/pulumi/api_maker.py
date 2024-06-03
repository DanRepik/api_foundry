import json
from typing import Any, Awaitable, Mapping, Optional, Sequence, Union, overload
from zipfile import ZipFile

import pulumi
from pulumi.output import Inputs
import pulumi_aws as aws

from api_maker.utils.logger import logger, DEBUG, write_logging_file
from api_maker.utils.model_factory import ModelFactory
from api_maker.iac.gateway_doc import GatewayDocument
from api_maker.cloudprints.python_archive_builder import PythonArchiveBuilder
from api_maker.cloudprints.pulumi.lambda_ import PythonFunctionCloudprint
from api_maker.cloudprints.pulumi.rest_api import GatewayAPICloudprint

log = logger(__name__)



class APIMaker(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        props: Mapping[str, Any | Awaitable[Any] | pulumi.Output[Any]],
        opts: pulumi.ResourceOptions | None = None,
        remote: bool = False,
    ) -> None:
        super().__init__("api_maker", name, props, opts, remote)

        api_spec = props.get("api_spec", None)
        assert api_spec, "api_spec is not set, a location must be provided."

        assert "secrets" in props, "Missing secrets map"

        api_maker_source = "/Users/clydedanielrepik/workspace/api_maker/src/api_maker"

        self.archive_builder = PythonArchiveBuilder(
            name=f"{name}-archive-builder",
            sources={
                "api_maker": api_maker_source,
                "api_spec.yaml": api_spec,
                "app.py": 
"""
import json
import logging
#from api_maker.adapters.gateway_adapter import GatewayAdapter
from api_maker.utils.model_factory import ModelFactory

log = logging.getLogger(__name__)

def lambda_handler(event, _):
    log.info(f"event: {event}")
    try:
        ModelFactory.load_spec("api_spec.yaml")
#        adapter = GatewayAdapter()
#        response = adapter.process_event(event)
        response = {}

        # Ensure the response conforms to API Gateway requirements
        return {
            "isBase64Encoded": False,
            "statusCode": response.get("statusCode", 200),
            "headers": response.get("headers", {"Content-Type": "application/json"}),
            "body": json.dumps(response.get("body", {}))
        }
    except Exception as e:
        log.error(f"exception: {e}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": f"exception: {e}"})
        }
"""
            },
            requirements=[
                "psycopg2-binary",
                "pyyaml",
                #                "-e /Users/clydedanielrepik/workspace/api_maker",
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
                "SECRETS": props["secrets"],
            },
        )

        ModelFactory.load_spec(api_spec)

        body=lambda_function.invoke_arn().apply(
            lambda invoke_arn: (
                GatewayDocument(
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

        pulumi.export("gateway-api", gateway.id)

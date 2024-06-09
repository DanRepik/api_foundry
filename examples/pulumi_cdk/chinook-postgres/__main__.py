import json
from zipfile import ZipFile

import pulumi
import pulumi_aws as aws

from api_maker.utils.logger import logger, DEBUG
from api_maker.iac.pulumi.api_maker import APIMaker
from api_maker.utils.model_factory import ModelFactory
from api_maker.iac.gateway_spec import GatewaySpec
from api_maker.cloudprints.python_archive_builder import PythonArchiveBuilder
from api_maker.cloudprints.pulumi.lambda_ import PythonFunctionCloudprint
from api_maker.cloudprints.pulumi.rest_api import GatewayAPICloudprint

log = logger(__name__)

api_maker_source = "/Users/clydedanielrepik/workspace/api_maker/src/api_maker"


api_maker = APIMaker(
    "chinook_postgres",
    props={
        "api_spec": "./chinook_api.yaml",
        "secrets": json.dumps({"postgres:chinook": "postgres/chinook"}),
    },
)

# /Users/clydedanielrepik/workspace/api_maker/examples/pulumi_cdk/chinook-postgres/venv/bin/python -m pip install --target temp/api-maker-lambda/libs --platform manylinux2010_x86_64 --implementation cp --only-binary=:all: --upgrade --python-version 3.9 -r temp/api-maker-lambda/staging/requirements.txt


"""
archive_builder = PythonArchiveBuilder(
    name=f"{pulumi.get_stack()}-archive-builder",
    sources={
      "api_maker": api_maker_source,
      "api_spec.yaml": "./chinook_api.yaml"
    },
    requirements=[
        "psycopg2-binary",
        "pyyaml",
        "-e /Users/clydedanielrepik/workspace/api_maker",
    ],
    working_dir="temp",
)

lambda_function = PythonFunctionCloudprint(
    name=f"{pulumi.get_stack()}-api-maker",
    hash=archive_builder.hash(),
    handler="api_maker.adapters.gateway_adapter.lambda_handler",
    archive_location=archive_builder.location(),
    environment={"SECRETS": json.dumps({"chinook-postgres": "postgres/chinook"})},
)

ModelFactory.load_spec("chinook_api.yaml")
gateway_document = lambda_function.invoke_arn().apply(
    lambda invoke_arn: (
        GatewayDocument(
            function_name=lambda_function.name,
            function_invoke_arn=invoke_arn,
            enable_cors=True,
        ).as_json()
    )
)

gateway = GatewayAPICloudprint(
    name=f"{pulumi.get_stack()}-api-maker",
    body=gateway_document,
)

log.info(f"gateway: {gateway.rest_api}")
pulumi.export("gateway-api", gateway.rest_api.id)

"""

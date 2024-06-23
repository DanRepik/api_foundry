import boto3
import os
import pytest
import json

from botocore.exceptions import ClientError

from api_maker.utils.model_factory import ModelFactory
from api_maker.utils.logger import logger

log = logger(__name__)


@pytest.fixture
def load_model():
    ModelFactory.load_yaml("resources/chinook_api.yaml")


def get_stack_output_value(stack_name: str, work_dir: str, output_name: str):
    from pulumi import automation as auto

    # Create or select a stack
    try:
        stack = auto.select_stack(
            stack_name=stack_name,
            work_dir=work_dir,
        )

        # Refresh the stack to get the latest outputs
        stack.refresh(on_output=print)

        # Get the stack outputs
        outputs = stack.outputs()
    except auto.errors.CommandError:
        return None

    # Return the requested output value
    return outputs[output_name].value if output_name in outputs else None


@pytest.fixture
def gateway_endpoint():
    api_id = get_stack_output_value("local", ".", "gateway-api")  # "nt5zecklg7"
    return f"http://{api_id}.execute-api.localhost.localstack.cloud:4566/dev"

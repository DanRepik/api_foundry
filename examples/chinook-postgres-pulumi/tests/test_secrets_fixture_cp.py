import boto3
import pytest

from botocore.exceptions import ClientError

from api_foundry.utils.model_factory import ModelFactory
from api_foundry.utils.logger import logger

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
        log.info(f"stack: {stack}")

        # Refresh the stack to get the latest outputs
        stack.refresh(on_output=print)
        log.info(f"stack: {stack}")

        # Get the stack outputs
        outputs = stack.outputs()
        log.info(f"outputs: {outputs}")
    except auto.errors.CommandError as ce:
        log.error(f"error: {ce}")
        return None

    # Return the requested output value
    return outputs[output_name].value if output_name in outputs else None


@pytest.fixture
def gateway_endpoint():
    log.info("gateway endpoint")
    api_id = get_stack_output_value("dev", ".", "gateway-api")  # "nt5zecklg7"
    return (
        f"http://{api_id}.execute-api.localhost.localstack.cloud:4566/chinook_postgres"
    )

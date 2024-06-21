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


def create_secret_if_not_exists(secret_name, secret_value):
    log.info("creating secret")
    # Create a Secrets Manager client
    client = boto3.client(
        "secretsmanager", endpoint_url="http://localhost.localstack.cloud:4566"
    )

    try:
        # Check if the secret already exists
        response = client.describe_secret(SecretId=secret_name)
        log.info(f"secret: {response}")
        log.info(f"Secret '{secret_name}' already exists!")
        return response["ARN"]
    except client.exceptions.ResourceNotFoundException:
        # Secret does not exist, proceed with creating it
        try:
            # Create the secret
            response = client.create_secret(Name=secret_name, SecretString=secret_value)
            log.info(f"Secret '{secret_name}' created successfully!")
            return response["ARN"]
        except ClientError as e:
            log.error(f"Failed to create secret '{secret_name}': {e}")
            return None
    except ClientError as e:
        log.error(f"Failed to check for secret '{secret_name}': {e}")
        return None


@pytest.fixture
def db_secrets():
    log.info("set secrets variable")
    os.environ["AWS_ENDPOINT_URL"] = "https://localhost.localstack.cloud:4566"
    os.environ["SECRETS"] = json.dumps({"chinook": "postgres/chinook"})
    create_secret_if_not_exists(
        "postgres/chinook",
        json.dumps(
            {
                "engine": "postgres",
                "dbname": "chinook",
                "username": "chinook_user",
                "password": "chinook_password",
                "host": "postgres_db",
            }
        ),
    )
    create_secret_if_not_exists(
        "oracle/chinook",
        json.dumps(
            {
                "engine": "oracle",
                "dbname": "XEPDB1",
                "username": "system",
                "password": "system",
                "host": "oracle_db",
            }
        ),
    )


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

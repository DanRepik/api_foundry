import json
import os
import boto3

from botocore.exceptions import ClientError

from api_maker.connectors.connection_factory import connection_factory
from api_maker.utils.logger import logger

log = logger(__name__)


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


secrets_map = json.dumps({"postgres|chinook": "postgres/chinook"})


def install_secrets():
    create_secret_if_not_exists(
        "postgres/chinook",
        json.dumps(
            {
                "dbname": "chinook",
                "username": "chinook_user",
                "password": "chinook_password",
                "host": "localhost",
            }
        ),
    )
    create_secret_if_not_exists(
        "oracle/chinook",
        json.dumps(
            {
                "dbname": "XEPDB1",
                "username": "system",
                "password": "system",
                "host": "localhost",
            }
        ),
    )


class TestSQLGenerator:

    def test_postgres_connection(self):
        os.environ["SECRETS_MAP"] = secrets_map

        connection = connection_factory("postgres", "chinook")

        assert connection is not None
        log.info(connection)

import os
import boto3
import pytest


@pytest.fixture
def secretsmanager():
    """Creates a boto3 client for Secrets Manager, using LocalStack if specified."""
    if os.getenv("AWS_PROFILE") == "localstack":
        return boto3.client(
            "secretsmanager",
            region_name="us-east-1",
            endpoint_url="https://localhost.localstack.cloud:4566",
        )
    else:
        return boto3.client("secretsmanager", region_name="us-east-1")


@pytest.fixture
def create_secret(secretsmanager):
    def _create_secret(secret_name, secret_value):
        try:
            secretsmanager.describe_secret(SecretId=secret_name)
        except secretsmanager.exceptions.ResourceNotFoundException:
            secretsmanager.create_secret(Name=secret_name, SecretString=secret_value)
        return secret_name

    return _create_secret


# Example test using the create_secret fixture
def test_secret_creation(create_secret, secretsmanager):
    secret_name = "my_test_secret"
    secret_value = '{"username": "test_user", "password": "test_pass"}'

    created_secret = create_secret(secret_name, secret_value)
    assert created_secret == secret_name

    # Verify the secret exists
    response = secretsmanager.get_secret_value(SecretId=secret_name)
    assert response["SecretString"] == secret_value


if __name__ == "__main__":
    pytest.main()

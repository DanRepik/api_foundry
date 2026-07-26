"""
Regression test: install_secret.py must not hardcode a LocalStack
endpoint.

install_secret is a registered production console-script
(api_foundry.scripts.install_secret:main), but previously always
constructed its boto3 Secrets Manager client with
endpoint_url="http://localhost.localstack.cloud:4566" - so running it
against real AWS silently talked to LocalStack instead of Secrets
Manager. The endpoint is now an explicit optional override, defaulting
to the AWS_ENDPOINT_URL environment variable or real AWS if unset.
"""

import pytest

from api_foundry.scripts.install_secret import create_secret_if_not_exists


class FakeSecretsManagerClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.exceptions = type(
            "Exceptions", (), {"ResourceNotFoundException": Exception}
        )

    def describe_secret(self, SecretId):
        raise self.exceptions.ResourceNotFoundException()

    def create_secret(self, Name, SecretString):
        return {"ARN": f"arn:aws:secretsmanager:us-east-1:123456789012:secret:{Name}"}


@pytest.mark.unit
def test_default_endpoint_is_not_localstack(monkeypatch):
    captured = {}

    def fake_boto3_client(service_name, **kwargs):
        captured.update(kwargs)
        return FakeSecretsManagerClient(**kwargs)

    monkeypatch.setattr(
        "api_foundry.scripts.install_secret.boto3.client", fake_boto3_client
    )

    create_secret_if_not_exists("my-secret", '{"engine": "postgres"}')

    assert captured.get("endpoint_url") is None


@pytest.mark.unit
def test_explicit_endpoint_url_is_passed_through(monkeypatch):
    captured = {}

    def fake_boto3_client(service_name, **kwargs):
        captured.update(kwargs)
        return FakeSecretsManagerClient(**kwargs)

    monkeypatch.setattr(
        "api_foundry.scripts.install_secret.boto3.client", fake_boto3_client
    )

    create_secret_if_not_exists(
        "my-secret",
        '{"engine": "postgres"}',
        endpoint_url="http://localhost.localstack.cloud:4566",
    )

    assert captured.get("endpoint_url") == "http://localhost.localstack.cloud:4566"

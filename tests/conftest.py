import json
import os
import pytest
import psycopg2
import pulumi
import pulumi_aws as aws
from pulumi import automation as auto

from pathlib import Path
from .automation_fixtures import deploy_stack, deploy_localstack
from .infrastructure_fixtures import exec_sql_file, postgres_container, localstack, test_network

os.environ["PULUMI_BACKEND_URL"] = "file://~"

DEFAULT_IMAGE = "localstack/localstack:latest"
DEFAULT_SERVICES = "logs,iam,lambda,secretsmanager,apigateway,cloudwatch"

def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("localstack")
    group.addoption(
        "--teardown",
        action="store",
        default="true",
        help="Whether to tear down the LocalStack/Postgres containers after tests (default: true)",
    )
    group.addoption(
        "--localstack-image",
        action="store",
        default=DEFAULT_IMAGE,
        help="Docker image to use for LocalStack (default: localstack/localstack:latest)",
    )
    group.addoption(
        "--localstack-services",
        action="store",
        default=DEFAULT_SERVICES,
        help="Comma-separated list of LocalStack services to start",
    )
    group.addoption(
        "--localstack-timeout",
        action="store",
        type=int,
        default=90,
        help="Seconds to wait for LocalStack to become healthy (default: 90)",
    )
    group.addoption(
        "--localstack-port",
        action="store",
        type=int,
        default=4566,
        help="Port for LocalStack edge service (default: 4566)",
    )

@pytest.fixture(scope="session")
def chinook_db(postgres_container):
    # Locate DDL files (project root is one parent up from this test file: backend/tests/ -> farm_market/)
    project_root = Path(__file__).resolve().parents[1]
    chinook_sql = project_root / "tests" / "Chinook_Postgres.sql"

    assert chinook_sql.exists(), f"Missing {chinook_sql}"

    # Connect and load schemas
    conn = psycopg2.connect(postgres_container["dsn"])
    try:
        conn.autocommit = True  # allow full scripts to run without transaction issues
        exec_sql_file(conn, chinook_sql)

        yield postgres_container

    finally:
        conn.close()


def chinook_api(chinook_db):
    def pulumi_program():
        from api_foundry import APIFoundry

        # Extract connection info from freemium_model
        conn_info = {
            "engine": "postgres",
            "host": chinook_db["host"],
            "port": chinook_db["port"],
            "username": chinook_db["user"],
            "password": chinook_db["password"],
            "dbname": chinook_db["database"],
            "dsn": chinook_db["dsn"],
        }

        secret = aws.secretsmanager.Secret("test-secret", name="test/secret")
        secret_value = aws.secretsmanager.SecretVersion(
            "test-secret-value",
            secret_id=secret.id,
            secret_string=json.dumps(conn_info),
        )

        # Create the FarmMarket component
        chinook_api = secret.arn.apply(lambda arn:
            APIFoundry(
                "chinook-api",
                api_spec="resources/chinook_api.yaml",
                secrets=json.dumps({"chinook": arn})
            )
        )
        pulumi.export("domain", chinook_api.domain)

    return pulumi_program

@pytest.fixture(scope="module")
def chinook_api_stack(chinook_db, localstack):
    stack, outputs, teardown = deploy_localstack(
        "chinook",
        "test",
        localstack,
        chinook_api(chinook_db),
        teardown=localstack.get("teardown", True),
    )
    yield outputs
    if teardown:
        stack.destroy(on_output=lambda _: None)
        stack.workspace.remove_stack("test")

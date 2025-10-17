import json
import os
from pathlib import Path

import pytest
import psycopg2
import pulumi
import pulumi_aws as aws
import yaml
from contextlib import contextmanager
import requests

from api_foundry_query_engine.utils.api_model import APIModel
from fixture_foundry import to_localstack_url
from fixture_foundry import deploy  # noqa F401
from fixture_foundry import exec_sql_file
from fixture_foundry import postgres  # noqa F401
from fixture_foundry import localstack  # noqa F401
from fixture_foundry import container_network  # noqa F401
from simple_oauth_server import SimpleOAuth

os.environ["PULUMI_BACKEND_URL"] = "file://."
# Ensure a consistent issuer for the SimpleOAuth authorizer and validator
os.environ.setdefault("ISSUER", "https://oauth.local/")

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
        default=0,
        help="Port for LocalStack edge service (default: 0 = random available port)",
    )
    group.addoption(
        "--database",
        action="store",
        type=str,
        default="chinook",
        help="Name of the database to use (default: chinook)",
    )
    group.addoption(
        "--database-image",
        action="store",
        type=str,
        default="postgis/postgis:16-3.4",
        help="Docker image to use for the database (default: chinook)",
    )


@pytest.fixture(scope="session")
def chinook_db(postgres):  # noqa F811
    # Locate DDL files (project root is one parent up from this test file: backend/tests/ -> farm_market/)
    project_root = Path(__file__).resolve().parents[1]
    chinook_sql = project_root / "tests" / "Chinook_Postgres.sql"

    assert chinook_sql.exists(), f"Missing {chinook_sql}"

    # Connect and load schemas
    dsn = f"postgresql://{postgres['username']}:{postgres['password']}@localhost:{postgres['host_port']}/{postgres['database']}"  # noqa E501

    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = True  # allow full scripts to run without transaction issues
        exec_sql_file(conn, chinook_sql)

        yield postgres

    finally:
        conn.close()


def chinook_api(chinook_db):
    def pulumi_program():
        from api_foundry import APIFoundry

        # Extract connection info from freemium_model
        conn_info = {
            "engine": "postgres",
            "host": chinook_db["container_name"],
            "port": chinook_db["container_port"],
            "username": chinook_db["username"],
            "password": chinook_db["password"],
            "database": chinook_db["database"],
            "dsn": chinook_db["dsn"],
        }

        secret = aws.secretsmanager.Secret("test-secret", name="test/secret")
        aws.secretsmanager.SecretVersion(
            "test-secret-value",
            secret_id=secret.id,
            secret_string=json.dumps(conn_info),
        )

        # OAuth server for tests
        oauth_server = SimpleOAuth("oauth", config=yaml.dump(TEST_USERS))

        # Create the Chinook component
        chinook_api = secret.arn.apply(
            lambda arn: APIFoundry(
                "chinook-api",
                api_spec=[
                    "resources/chinook_api.yaml",
                    oauth_server.authorizer_api_spec,
                ],
                integrations=[
                    {
                        "path": "/token",
                        "method": "post",
                        "function": oauth_server.authorizer(),
                    }
                ],
                token_validators=[
                    {
                        "name": "oauth",
                        "type": "token",
                        "function": oauth_server.validator(),
                    }
                ],
                secrets=json.dumps({"chinook": arn}),
            )
        )
        pulumi.export("domain", chinook_api.domain)

    return pulumi_program


TEST_USERS: dict = {
    "clients": {
        "user_sales_reader": {
            "client_secret": "sales-reader-secret",
            "audience": "chinook-api",
            "sub": "user_sales_reader",
            "scope": "read:*",
            "roles": ["sales_reader"],
        },
        "user_sales_associate": {
            "client_secret": "sales-associate-secret",
            "audience": "chinook-api",
            "sub": "user_sales_associate",
            "scope": "read:* write:*",
            "roles": ["sales_associate"],
        },
        "user_sales_manager": {
            "client_secret": "sales-manager-secret",
            "audience": "chinook-api",
            "sub": "user_sales_manager",
            "scope": "read:* write:* delete:*",
            "roles": ["sales_manager"],
        },
    }
}


@pytest.fixture(scope="module")
def chinook_api_stack(request, chinook_db, localstack):  # noqa F811
    teardown = request.config.getoption("--teardown").lower() == "true"
    with deploy(
        "api-foundry",
        "test-api",
        chinook_api(chinook_db),
        localstack=localstack,
        teardown=teardown,
    ) as outputs:
        yield outputs


@pytest.fixture(scope="module")
def chinook_api_endpoint(chinook_api_stack, localstack):  # noqa F811
    domain = chinook_api_stack["domain"]
    port = localstack["port"]
    yield to_localstack_url(f"https://{domain}", port)


@pytest.fixture(scope="module")
def load_api_model():
    filename = os.path.join(os.getcwd(), "resources/api_spec.yaml")
    with open(filename, "r") as file:
        yield APIModel(yaml.safe_load(file))


@pytest.fixture(scope="module")
def chinook_api_model():
    filename = os.path.join(os.getcwd(), "resources/chinook_api.yaml")
    with open(filename, "r") as file:
        yield yaml.safe_load(file)


@pytest.fixture(scope="module")
def sales_associate(chinook_api_endpoint: str):
    user = TEST_USERS["clients"]["user_sales_associate"]

    resp = requests.post(
        f"{chinook_api_endpoint}/token",
        json={
            "grant_type": "client_credentials",
            "client_id": user["sub"],
            "client_secret": user["client_secret"],
            "audience": user["audience"],
            "scope": user["scope"],
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    result = resp.json()
    yield result["token"]

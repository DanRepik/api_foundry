import json
import logging
import os
from pathlib import Path

import pytest

try:
    import psycopg2
except ImportError:
    psycopg2 = None

import pulumi
import pulumi_aws as aws
import yaml
import requests

from api_foundry_query_engine.utils.api_model import APIModel
from fixture_foundry import to_localstack_url
from fixture_foundry import deploy  # noqa F401
from fixture_foundry import exec_sql_file
from fixture_foundry import postgres  # noqa F401
from fixture_foundry import localstack  # noqa F401
from fixture_foundry import container_network  # noqa F401
from simple_oauth_server import SimpleOAuth

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Ensure a consistent issuer for the SimpleOAuth authorizer and validator
os.environ.setdefault("ISSUER", "https://oauth.local/")


def to_localstack_internal_url(_localstack, aws_gateway_endpoint: str) -> str:
    """
    Convert AWS API Gateway endpoint to LocalStack internal container format.

    Args:
        localstack: LocalStack fixture with container_name and container_port
        aws_gateway_endpoint: AWS Gateway endpoint like
                             "jjhkkvcjf0.execute-api.us-east-1.amazonaws.com/oauth-rest-api"

    Returns:
        LocalStack internal URL like
        "http://container_name:container_port/restapis/jjhkkvcjf0/oauth-rest-api/_user_request_/path"
    """
    # Remove any protocol prefix if present
    endpoint = aws_gateway_endpoint.replace("https://", "").replace("http://", "")

    # Split the endpoint into parts
    # Format: api-id.execute-api.region.amazonaws.com/stage
    parts = endpoint.split("/")
    domain_part = parts[0]  # api-id.execute-api.region.amazonaws.com
    stage = parts[1] if len(parts) > 1 else ""  # stage part

    # Extract API ID from domain
    api_id = domain_part.split(".")[0]  # jjhkkvcjf0

    # Build LocalStack internal URL using container name and port from fixture
    # Format: http://container_name:container_port/restapis/{api_id}/{stage}/_user_request_{path}
    # Use container name and port for container-to-container communication
    log.debug("localstack info: %s", _localstack)
    container_host = _localstack["container_name"]
    container_port = _localstack["container_port"]
    base_url = f"http://{container_host}:{container_port}/restapis/{api_id}"

    if stage:
        base_url += f"/{stage}"

    base_url += "/_user_request_"
    return base_url


def pytest_addoption(parser: pytest.Parser) -> None:
    # Import and use fixture_foundry's default pytest options
    # This includes --teardown option with default behavior
    from fixture_foundry import add_fixture_foundry_options

    add_fixture_foundry_options(parser)


@pytest.fixture(scope="session")
def chinook_db(postgres):  # noqa F811
    # Locate DDL files (project root is one parent up from this test file: backend/tests/ -> farm_market/)
    project_root = Path(__file__).resolve().parents[1]
    chinook_sql = project_root / "tests" / "Chinook_Postgres.sql"

    assert chinook_sql.exists(), f"Missing {chinook_sql}"

    if psycopg2 is None:
        pytest.skip("psycopg2 not installed, skipping database test")

    # Connect and load schemas
    dsn = f"postgresql://{postgres['username']}:{postgres['password']}@localhost:{postgres['host_port']}/{postgres['database']}"  # noqa E501

    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = True  # allow full scripts to run without transaction issues
        exec_sql_file(conn, chinook_sql)

        yield postgres

    finally:
        conn.close()


def chinook_api(chinook_db, localstack):  # noqa F811
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
        oauth_server = SimpleOAuth(
            "oauth",
            config=yaml.dump(TEST_USERS),
            issuer=os.environ["ISSUER"],
        )

        # Create the Chinook component
        chinook_api = pulumi.Output.all(secret.arn, oauth_server.server.domain).apply(
            lambda args: APIFoundry(
                "chinook-api",
                api_spec=[
                    "resources/chinook_api.yaml",
                    oauth_server.authorizer_api_spec,
                ],
                environment={
                    "LOG_LEVEL": "DEBUG",
                    "JWKS_HOST": to_localstack_internal_url(
                        localstack, f"http://{args[1]}"
                    ),
                    "JWT_ISSUER": oauth_server.issuer,
                    "JWT_ALLOWED_AUDIENCES": TEST_AUDIENCE,
                    "REQUIRE_AUTHENTICATION": "FALSE",
                },
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
                secrets=json.dumps({"chinook": args[0]}),
            )
        )
        pulumi.export("domain", chinook_api.domain)

    return pulumi_program


TEST_AUDIENCE = "chinook-api"
TEST_USERS: dict = {
    "clients": {
        "user_sales_reader": {
            "client_secret": "sales-reader-secret",
            "audience": TEST_AUDIENCE,
            "sub": "user_sales_reader",
            "scope": "read:*",
            "roles": ["sales_reader"],
        },
        "user_sales_associate": {
            "client_secret": "sales-associate-secret",
            "audience": TEST_AUDIENCE,
            "sub": "user_sales_associate",
            "scope": "read:* write:*",
            "roles": ["sales_associate"],
        },
        "user_sales_manager": {
            "client_secret": "sales-manager-secret",
            "audience": TEST_AUDIENCE,
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
        chinook_api(chinook_db, localstack),
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


# Removed pytest_configure to allow normal command line option handling

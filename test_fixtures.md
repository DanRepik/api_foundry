# Rich, Realistic Integration Testing with pytest Fixtures: Postgres + LocalStack

Provisioning real AWS infrastructure inside tests can be slow and costly—especially databases like RDS, which are not designed for ephemeral, per-test lifecycles. Instead, you can run realistic, hermetic integration tests locally by combining Dockerized Postgres with LocalStack for AWS services, all orchestrated via pytest fixtures.

In this article, we’ll build a fast, reproducible test environment that:
- Uses LocalStack to emulate AWS services (API Gateway, Lambda, Secrets Manager, CloudWatch, etc.).
- Runs a Postgres container seeded with real test data.
- Leverages Pulumi Automation API to deploy and tear down infra on demand.
- Provides pytest fixtures with clear scopes and health checks to avoid flakiness.

The result is a one-command workflow that exercises your Lambda + API + database path without touching real AWS, while remaining close to production semantics.

## What you’ll build
* A dedicated Docker network all containers can join
* A Postgres container with a test schema (Chinook)
* A LocalStack container exposing AWS services
* A Pulumi “deploy” context manager to create/destroy infra on demand
* Helpers to convert real AWS URLs to LocalStack URLs
* CLI toggles to control teardown, images, ports, and timeouts

## Prerequisites

* Docker Desktop (Mac)
* Python 3.11+ and pytest
pip packages: docker, psycopg2-binary, requests, pulumi, pulumi-aws, pytest, pyyaml
* LocalStack image pulled automatically by the fixture

Install the Python deps:

## Understanding PyTest Fixtures

Pytest fixtures are used to install the various resources for the test environment.  So a brief explantation of how these fixtures work is in order.

Fixtures can also perform cleanup or teardown actions after the test code has finished executing. This is achieved by placing code after the `yield` statement in the fixture. When the test using the fixture completes, pytest resumes execution after the `yield`, allowing you to destroy resources, stop containers, or perform any necessary cleanup. This pattern ensures that setup and teardown logic are colocated and reliably executed.

Example:

```python
@pytest.fixture
def resource():
    # Setup code
    yield some_resource
    # Teardown code runs after the test
```
In pytest, fixtures can depend on other fixtures by declaring them as arguments in the fixture function. When you request a fixture as a parameter, pytest automatically resolves and injects the dependencies.

Example:

```python
# Suppose you have a fixture that sets up a database connection
import pytest

@pytest.fixture
def db_connection():
    # Setup code
    conn = "db_conn_object"
    yield conn
    # Teardown code

# Another fixture can depend on db_connection
@pytest.fixture
def user(db_connection):
    # Use db_connection to create a user
    user = f"user_using_{db_connection}"
    return user

def test_example(user):
    assert "user_using_db_conn_object" == user
```

### Key points:

* Pytest resolves fixture dependencies recursively.
* You can chain fixtures as needed.
* This promotes modular, reusable test setup code.

If two fixtures depend on the same lower-level fixture, pytest will only set up and tear down that lower-level fixture once per test (unless you change the fixture’s scope).

## Core fixtures and helpers

Common fixtures are loc
Below are distilled patterns you can adapt.

* A reusable Docker network so containers can talk by name.
* A Postgres fixture that exposes both container-to-container and host-to-container connectivity.
* A LocalStack fixture that waits for health and enables Lambda-to-Postgres via the same network.
* A Pulumi deploy context manager to create a stack and yield outputs.
* A URL helper to hit LocalStack’s API Gateway edge endpoint.

pip install pytest docker psycopg2-binary requests pulumi pulumi-aws pyyamlnstall the Python deps:

Install the python dependiences.

pip install pytest docker psycopg2-binary requests pulumi pulumi-aws pyyaml

## Core fixtures and helpers

The infrstructure_fixtures.py file contains a pallette of fixtures.  

Building test infrastructure for a test suite consists of using those fixtures.  Typically this is done in the conftest.py file for the test suite.

## Core fixtures and helpers

The core fixtures provided by the infrastructure_fixtures.py file are;

* postgres - this session scoped fixture will start up a postgres container.  
* localstack - this session scoped container will start a localstack container.

Additionally some utility functions are provided;

* exec_sql_file - allows executing SQL file into the postgres database.
* deploy - uses Pulumi automation to deploy your infrastructure resources.



## Key points:

* The Postgres fixture exposes container_name:container_port to other containers (e.g., Lambda) and localhost:host_port to the host tests.
* The LocalStack fixture puts Lambda containers on the same network using LAMBDA_DOCKER_NETWORK, which is essential for cross-container connectivity.
* Health checks and port mapping retries eliminate race conditions.

<!-- copilot: discuss how the infratructure_fixtures contaion reusable element.  And the the content of the test suite conftest.py contains set up specific for the suite
-->

## CLI options with pytest

Expose tunables via pytest_addoption so CI and local runs can vary behavior without code edits.

```python
import pytest

DEFAULT_IMAGE = "localstack/localstack:latest"
DEFAULT_SERVICES = "logs,iam,lambda,secretsmanager,apigateway,cloudwatch"

def pytest_addoption(parser: pytest.Parser) -> None:
    g = parser.getgroup("localstack")
    g.addoption("--teardown", action="store", default="true")
    g.addoption("--use-localstack", action="store", default="true")
    g.addoption("--localstack-image", action="store", default=DEFAULT_IMAGE)
    g.addoption("--localstack-services", action="store", default=DEFAULT_SERVICES)
    g.addoption("--localstack-timeout", action="store", type=int, default=90)
    g.addoption("--localstack-port", action="store", type=int, default=0)
    g.addoption("--database", action="store", type=str, default="chinook")
    g.addoption("--database-image", action="store", type=str, default="postgis/postgis:16-3.4")
```

## Loading a test database

Load a real schema once per session for realistic queries. Example with the Chinook sample:

```python
import psycopg2
from pathlib import Path
import pytest

def exec_sql_file(conn, sql_path: Path):
    with conn, conn.cursor() as cur:
        cur.execute(sql_path.read_text(encoding="utf-8"))

@pytest.fixture(scope="session")
def chinook_db(postgres):
    sql = Path("tests/Chinook_Postgres.sql")
    assert sql.exists(), f"Missing {sql}"
    conn = psycopg2.connect(postgres["dsn"])
    try:
        conn.autocommit = True
        exec_sql_file(conn, sql)
        yield postgres
    finally:
        conn.close()
```

## Deploying infra under test with Pulumi

Use Pulumi Automation API to stand up the system under test dynamically, then tear it down automatically.

```python
import json
import pulumi_aws as aws
import pulumi

def api_program(chinook_db):
    def program():
        from api_foundry import APIFoundry
        conn = {
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
            "test-secret-value", secret_id=secret.id, secret_string=json.dumps(conn)
        )
        api = secret.arn.apply(lambda arn: APIFoundry(
            "chinook-api",
            api_spec="resources/chinook_api.yaml",
            secrets=json.dumps({"chinook": arn}),
        ))
        pulumi.export("domain", api.domain)
    return program
```

```python
@pytest.fixture(scope="module")
def chinook_api_stack(chinook_db, localstack, request):
    teardown = request.config.getoption("--teardown").lower() == "true"
    with deploy(
        "api-foundry",
        "test-api",
        api_program(chinook_db),
        localstack=localstack,
        teardown=teardown,
    ) as outputs:
        yield outputs

@pytest.fixture(scope="module")
def chinook_api_endpoint(chinook_api_stack, localstack):
    domain = chinook_api_stack["domain"]
    port = int(localstack["port"])
    yield to_localstack_url(f"https://{domain}", port)
```

## Why this works well

* Realistic: Real Postgres and AWS-compatible services catch integration issues early.
* Deterministic: Health checks, retries, and scoped fixtures reduce flakiness.
* Fast: Session/module scoping avoids repeated container startups.
* Portable: Everything runs locally via Docker; CI can run the same command.

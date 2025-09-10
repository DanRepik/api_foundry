import os
import time
from typing import Dict, Generator, Optional
from pathlib import Path

import docker
import psycopg2
import pytest
import requests

from docker.errors import DockerException
from docker.types import Mount

os.environ["PULUMI_BACKEND_URL"] = "file://~"
DEFAULT_REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))

@pytest.fixture(scope="session")
def test_network(request: pytest.FixtureRequest) -> Generator[str, None, None]:
    """
    Ensure a user-defined Docker network exists for cross-container comms
    (e.g., LocalStack Lambdas <-> Postgres). Yields the network name.
    Respects DOCKER_TEST_NETWORK env var; defaults to 'ls-dev'.
    """
    network_name = os.environ.get("DOCKER_TEST_NETWORK", "ls-dev")
    client = docker.from_env()

    net = None
    for n in client.networks.list(names=[network_name]):
        if n.name == network_name:
            net = n
            break

    created = False
    if net is None:
        net = client.networks.create(network_name, driver="bridge")
        created = True

    try:
        yield network_name
    finally:
        # Remove only if we created it and teardown is enabled
        teardown_opt = getattr(request.config.option, "teardown", "true")
        teardown = str(teardown_opt).lower() in ("1", "true", "yes", "y")
        if created and teardown:
            try:
                net.remove()
            except Exception:
                pass



def exec_sql_file(conn, sql_path: Path):
    sql_text = sql_path.read_text(encoding="utf-8")
    # Execute entire script (supports DO $$ ... $$ blocks and multiple statements)
    with conn.cursor() as cur:
        cur.execute(sql_text)

@pytest.fixture(scope="session")
def postgres_container(request: pytest.FixtureRequest, test_network) -> Generator[dict, None, None]:
    """
    Starts a PostgreSQL container and yields connection info.
    Uses a random host port mapped to 5432.
    """
    teardown: bool = request.config.getoption("--teardown").lower() == "true"
    try:
        client = docker.from_env()
        client.ping()
    except Exception as e:
        assert False, f"Docker not available: {e}"

    user = "test_user"
    password = "test_password"
    database = "chinook"
    image = "postgis/postgis:16-3.4"
    host_name = "postgres"
    # Let Docker assign a free host port; we’ll resolve it after start
    # Use None to let Docker assign a random host port
    host_port = None

    container = client.containers.run(
        image,
        name=f"query-engine-test-{int(time.time())}",
        hostname=host_name,
        environment={
            "POSTGRES_USER": user,
            "POSTGRES_PASSWORD": password,
            "POSTGRES_DB": database,
        },
        ports={"5432/tcp": host_port},  # bind to all interfaces; pick free host port
        network=test_network,
        detach=True,
    )

    try:
        # Resolve mapped host port with retries
        host_port = None
        for _ in range(20):
            container.reload()
            try:
                port_info = container.attrs["NetworkSettings"]["Ports"]["5432/tcp"]
                if port_info and port_info[0] and port_info[0].get("HostPort"):
                    host_port = int(port_info[0]["HostPort"])
                    break
            except Exception:
                pass
            time.sleep(0.5)
        assert host_port, "Failed to discover mapped Postgres host port"

        # Wait for readiness from the HOST perspective (127.0.0.1:<host_port>)
        deadline = time.time() + 90
        while time.time() < deadline:
            try:
                conn = psycopg2.connect(
                    dbname=database, user=user, password=password, host="127.0.0.1", port=host_port
                )
                conn.close()
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("Postgres did not become ready in time")

        yield {
            # For Lambda/containers on the same Docker network:
            "host": host_name,
            "port": 5432,
            "user": user,
            "password": password,
            "database": database,
            # For host/macOS access:
            "dsn": f"postgresql://{user}:{password}@127.0.0.1:{host_port}/{database}",
        }
    finally:
        if teardown:
            try:
                container.stop(timeout=5)
            except Exception:
                pass
            try:
                container.remove(v=True, force=True)
            except Exception:
                pass

def _wait_for_localstack(endpoint: str, timeout: int = 90) -> None:
    """Wait until LocalStack health endpoint reports ready or timeout expires."""
    url_candidates = [
        f"{endpoint}/_localstack/health",  # modern health endpoint
        f"{endpoint}/health",  # legacy fallback
    ]

    start = time.time()
    last_err: Optional[str] = None
    while time.time() - start < timeout:
        for url in url_candidates:
            try:
                resp = requests.get(url, timeout=2)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                    except Exception:
                        data = {}
                    # Heuristics: consider healthy if initialized true or services reported
                    if isinstance(data, dict):
                        if data.get("initialized") is True:
                            return
                        if "services" in data:
                            # services dict often present when up
                            return
                    else:
                        return
            except Exception as e:  # noqa: PERF203 - simple polling loop
                last_err = str(e)
                time.sleep(0.5)
                continue
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for LocalStack at {endpoint} (last_err={last_err})")

@pytest.fixture(scope="session")
def localstack(request: pytest.FixtureRequest, test_network) -> Generator[Dict[str, str], None, None]:
    """
    Session-scoped fixture that runs a LocalStack container.

    Yields a dict with:
      - endpoint_url: Edge endpoint URL (e.g., http://127.0.0.1:4566)
      - region: AWS region configured
      - container_id: Docker container id
      - services: comma list of services configured
    """
    teardown: bool = request.config.getoption("--teardown").lower() == "true"
    port: int = int(request.config.getoption("--localstack-port"))
    image: str = request.config.getoption("--localstack-image")
    services: str = request.config.getoption("--localstack-services")
    timeout: int = int(request.config.getoption("--localstack-timeout"))

    if docker is None:
        assert False, "Docker SDK not available: skipping LocalStack-dependent tests"

    try:
        client = docker.from_env()
    except DockerException:
        assert False, "Docker daemon not available: skipping LocalStack-dependent tests"

    # Pull image to ensure availability
    try:
        client.images.pull(image)
    except Exception:
        # If pull fails, we may already have it locally — proceed
        pass

    # Publish only the edge port; service port range is not needed with edge
    ports = {
        "4566/tcp": port,
    }
    env = {
        "SERVICES": services,
        "LS_LOG": "warn",
        "AWS_DEFAULT_REGION": DEFAULT_REGION,
        "LAMBDA_DOCKER_NETWORK": test_network,  # ensure Lambda containers join this network
        "DISABLE_CORS_CHECKS": "1",
    }
    # Mount Docker socket for LocalStack to access Docker if needed
    volume_dir = os.environ.get("LOCALSTACK_VOLUME_DIR", "./volume")
    mounts = [
        Mount(
            target="/var/run/docker.sock",
            source="/var/run/docker.sock",
            type="bind",
            read_only=False,
        ),
        Mount(
            target="/var/lib/localstack",
            source=os.path.abspath(volume_dir),
            type="bind",
            read_only=False,
        ),
    ]
    container = client.containers.run(
        image,
        detach=True,
        environment=env,
        ports=ports,
        name=None,
        tty=False,
        auto_remove=True,
        mounts=mounts,
        network=test_network,
    )

    if port == 0:
        # Resolve host port assigned for edge, with retries to avoid race condition
        host_port = None
        max_attempts = 10
        for attempt in range(max_attempts):
            container.reload()
            try:
                port_info = container.attrs["NetworkSettings"]["Ports"]["4566/tcp"]
                if port_info and port_info[0] and port_info[0].get("HostPort"):
                    host_port = int(port_info[0]["HostPort"])  # type: ignore[arg-type]
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if host_port is None:
            # Clean up if mapping not available
            try:
                container.stop(timeout=5)
            finally:
                raise RuntimeError("Failed to determine LocalStack edge port after retries")
    else:
        host_port = port

    endpoint = f"http://127.0.0.1:{host_port}"

    # Set common AWS envs for child code that relies on defaults
    os.environ.setdefault("AWS_REGION", DEFAULT_REGION)
    os.environ.setdefault("AWS_DEFAULT_REGION", DEFAULT_REGION)
    os.environ.setdefault("AWS_ACCESS_KEY_ID", os.environ.get("AWS_ACCESS_KEY_ID", "test"))
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", os.environ.get("AWS_SECRET_ACCESS_KEY", "test"))

    # Wait for the health endpoint to be ready
    _wait_for_localstack(endpoint, timeout=timeout)

    try:
        yield {
            "endpoint_url": endpoint,
            "region": DEFAULT_REGION,
            "container_id": str(container.id),
            "services": services,
        }
    finally:
        if teardown:
            # Stop container if still running
            try:
                container.stop(timeout=5)
            except Exception:
                pass

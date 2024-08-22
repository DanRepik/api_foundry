import pytest

from api_foundry.connectors.connection_factory import connection_factory
from api_foundry.utils.logger import logger

from test_fixtures import db_secrets

log = logger(__name__)


@pytest.mark.integration
class TestPostgresConnection:
    def test_postgres_connection(self, db_secrets):
        connection = connection_factory.get_connection("chinook")

        log.info(f"connection: {connection}")

        assert connection is not None

import json
import os
import boto3

from botocore.exceptions import ClientError

from api_maker.connectors.connection_factory import connection_factory
from api_maker.utils.logger import logger

from test_fixtures import db_secrets

log = logger(__name__)


class TestPostgresConnection:
    def test_postgres_connection(self, db_secrets):
        connection = connection_factory.get_connection("chinook")

        log.info(f"connection: {connection}")

        assert connection is not None

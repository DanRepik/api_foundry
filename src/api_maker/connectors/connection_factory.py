import json
import os

from api_maker.connectors.connection import Connection
from api_maker.utils.logger import logger

log = logger(__name__)

__secrets_map = None


def secrets_map() -> dict:
    global __secrets_map
    if not __secrets_map:
        log.info(f"secrets_map; {os.environ.get('SECRETS')}")
        __secrets_map = json.loads(os.environ.get("SECRETS", "{}"))
    return __secrets_map


def connection_factory(engine: str, database: str) -> Connection:
    """
    Factory function to create a database connector based on the
    specified engine and schema.

    Args:
    - engine (str): The database engine type
            ('postgres', 'oracle', or 'mysql').
    - schema (str): The schema for the database.

    Returns:
    - Connector: An instance of the appropriate Connector subclass.
    """

    # Get the secret name based on the engine and database from the secrets map
    log.info(f"engine: {engine}, database: {database}")
    secret_name = secrets_map().get(f"{engine}:{database}")
    log.info(f"secret_name: {secret_name}")

    if secret_name:
        if engine == "postgres":
            from .postgres_connection import PostgresConnection

            return PostgresConnection(db_secret_name=secret_name)
        # Add support for other engines here if needed in the future
        else:
            raise ValueError(f"Unsupported database engine: {engine}")
    else:
        raise ValueError(f"Secret not found for database: {database}")

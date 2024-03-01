import json
import os

from api_maker.connectors.connector import Connector
from api_maker.utils.logger import logger

# Load secrets map once during import
SECRETS_MAP = json.loads(os.environ.get("SECRETS_MAP", "{}"))

def connector_factory(engine: str, database: str) -> Connector:
    """
    Factory function to create a database connector based on the specified engine and schema.

    Args:
    - engine (str): The database engine type ('postgres', 'oracle', or 'mysql').
    - schema (str): The schema for the database.

    Returns:
    - Connector: An instance of the appropriate Connector subclass.
    """

    # Get the secret name based on the engine and database from the secrets map
    secret_name = SECRETS_MAP.get(f"{engine}|{database}")

    if secret_name:
        if engine == "postgres":
            from .postgres_connector import PostgresConnector
            return PostgresConnector(db_secret_name=secret_name)
        # Add support for other engines here if needed in the future
        else:
            raise ValueError(f"Unsupported database engine: {engine}")
    else:
        raise ValueError(f"Secret not found for database: {database}")


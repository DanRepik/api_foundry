from api_maker.connectors.connector import Connector
from api_maker.utils.logger import logger

from psycopg2 import Error, IntegrityError, ProgrammingError, connect

# Initialize the logger
log = logger(__name__)

class PostgresConnector(Connector):
    def get_connection(self):
        """
        Get a connection to the PostgreSQL database.

        Parameters:
        - schema (str, optional): The database schema to set for the connection.

        Returns:
        - connection: A connection to the PostgreSQL database.
        """
        dbname = self.db_config["dbname"]
        user = self.db_config["username"]
        password = self.db_config["password"]
        host = self.db_config["host"]
        port = self.db_config("port", 5432)
        search_path = self.db_config("search_path", None)

        log.info(f"dbname={dbname}, user={user}, host={host}, port={port}, search_path={search_path}")

        # Create a connection to the PostgreSQL database
        return connect(
            dbname=dbname, user=user, password=password, host=host, port=port,
            options="-c search_path={0}".format(search_path) if search_path else None
        )

    def execute_sql(self, cursor, sql: str, parameters: dict):
        """
        Execute SQL statements on the PostgreSQL database.

        Parameters:
        - cursor: The database cursor.
        - sql (str): The SQL statement to execute.
        - parameters (dict): Parameters to be used in the SQL statement.

        Returns:
        - None

        Raises:
        - AppException: Custom exception for handling database-related errors.
        """
        log.info(f"sql: {cursor.mogrify(sql, parameters)}")

        try:
            # Execute the SQL statement with parameters
            cursor.execute(sql, parameters)
        except IntegrityError as err:
            # Handle integrity constraint violation (e.g., duplicate key)
            raise Exception(409, err.pgerror)
        except ProgrammingError as err:
            # Handle programming errors (e.g., syntax error in SQL)
            raise Exception(400, err.pgerror)
        except Error as err:
            # Handle other database errors
            raise Exception(500, err.pgerror)

import json
import os
import re

from api_maker.utils.logger import logger
from api_maker.utils.app_exception import ApplicationException

# Initialize the logger
log = logger(__name__)

db_config_map = dict()

class Cursor:
    def execute(self, sql: str, params: dict) -> list[tuple]:
        raise NotImplemented    

    def close(self):
        raise NotImplementedError  

class Connector:
    def __init__(self, db_secret_name: str) -> None:
        super().__init__()
        self.db_config = self.get_db_config(db_secret_name)

    def cursor(self) -> Cursor:
        raise NotImplementedError
    
    def commit(self):
        raise NotImplementedError

    def get_db_config(self, db_secret_name: str):
        """
        Set the database configuration based on the secret name.

        Parameters:
        - db_secret_name (str): The name of the AWS Secrets Manager secret.

        Returns:
        - None
        """
        # Try to load secret from global cache
        global db_config_map
        db_config = db_config_map.get(db_secret_name, None)

        # If the cache is not found, get the secret from AWS Secrets Manager
        # and add it to the cache object.
        if not db_config:
            log.info(f"db_config not cached {db_secret_name}")
            db_config = self.__get_secret(db_secret_name)
            db_config_map[db_secret_name] = db_config

        return db_config            

    def __get_secret(self, db_secret_name: str):
        """
        Get the secret from AWS Secrets Manager.

        Parameters:
        - db_secret_name (str): The name of the AWS Secrets Manager secret.

        Returns:
        - dict: The database configuration obtained from the secret.
        """
        import boto3
        
        sts_client = boto3.client('sts')

        secret_account_id = os.environ.get("SECRET_ACCOUNT_ID", None)

        if secret_account_id:
            # If a secret account ID is provided, assume a role in that account
            secret_role = os.environ.get("ROLE_NAME", None)
            assume_role_response = sts_client.assume_role(
                RoleArn=f"arn:aws:iam::{secret_account_id}:role/{secret_role}",
                RoleSessionName='AssumeRoleSession'
            )

            credentials = assume_role_response['Credentials']

            secretsmanager = boto3.client(
                'secretsmanager',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
        else:
            # If no secret account ID is provided, use the default account
            secretsmanager = boto3.client("secretsmanager")

        # Get the secret value from AWS Secrets Manager
        db_secret = secretsmanager.get_secret_value(SecretId=db_secret_name)
        log.debug(f"loading secret name: {db_secret_name}")

        # Return the parsed JSON secret string
        return json.loads(db_secret.get("SecretString"))
    
    def close(self):
        raise NotImplementedError



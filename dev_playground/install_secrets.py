#!/usr/bin/env python3

import boto3
import json

from botocore.exceptions import ClientError


def create_secret_if_not_exists(secret_name, secret_value):
    # Create a Secrets Manager client
    client = boto3.client(
        "secretsmanager", endpoint_url="http://localhost.localstack.cloud:4566"
    )

    try:
        # Check if the secret already exists
        response = client.describe_secret(SecretId=secret_name)
        return response["ARN"]
    except client.exceptions.ResourceNotFoundException:
        # Secret does not exist, proceed with creating it
        try:
            # Create the secret
            response = client.create_secret(Name=secret_name, SecretString=secret_value)
            print(f"Secret '{secret_name}' created successfully!")
            return response["ARN"]
        except ClientError as e:
            print(f"Failed to create secret '{secret_name}': {e}")
            return None
    except ClientError as e:
        print(f"Failed to check for secret '{secret_name}': {e}")
        return None


create_secret_if_not_exists(
    "postgres/chinook",
    json.dumps(
        {
            "engine": "postgres",
            "dbname": "chinook",
            "username": "chinook_user",
            "password": "chinook_password",
            "host": "postgres_db",
        }
    ),
)
create_secret_if_not_exists(
    "oracle/chinook",
    json.dumps(
        {
            "engine": "oracle",
            "dbname": "XEPDB1",
            "username": "system",
            "password": "system",
            "host": "oracle_db",
        }
    ),
)

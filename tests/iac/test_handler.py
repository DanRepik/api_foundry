import os
import json
import boto3
import pytest
from api_maker.utils.app_exception import ApplicationException
from api_maker.adapters.gateway_adapter import GatewayAdapter
from api_maker.utils.model_factory import ModelFactory
from api_maker.iac.handler import lambda_handler  # Replace 'your_module' with the actual module name

@pytest.fixture(scope='module')
def secretsmanager_client():
    return boto3.client('secretsmanager', region_name='us-east-1', endpoint_url='http://localhost:4566')

@pytest.fixture(scope='module')
def create_secret(secretsmanager_client):
    secret_name = "postgres/chinook-local"
    secret_value = json.dumps({
        "dielect": "postgres",
        "dbname": "chinook",
        "username": "chinook_user",
        "password": "chinook_password",
        "host": "localhost"
    })

    try:
        secretsmanager_client.create_secret(
            Name=secret_name,
            SecretString=secret_value
        )
    except secretsmanager_client.exceptions.ResourceExistsException:
        pass

    return secret_name

@pytest.fixture(autouse=True)
def set_environment_variables(create_secret):
    os.environ['SECRETS']= json.dumps({"postgres:chinook": "postgres/chinook-local"})
    os.environ['API_SPEC']= "resources/chinook_api.yaml"
    

    event = {
        'path': '/album',
        'headers': {
            'Host': 'localhost',
            'User-Agent': 'python-requests/2.25.1',
            'accept-encoding': 'gzip, deflate',
            'accept': '*/*',
            'Connection': 'keep-alive'
        },
        'body': '',
        'isBase64Encoded': False,
        'httpMethod': 'GET',
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'pathParameters': {},
        'resource': '/album',
        'requestContext': {
            'accountId': '000000000000',
            'apiId': 'local',
            'resourcePath': '/album',
            'domainPrefix': 'localhost',
            'domainName': 'localhost',
            'resourceId': 'resource-id',
            'requestId': 'request-id',
            'identity': {
                'accountId': '000000000000',
                'sourceIp': '127.0.0.1',
                'userAgent': 'python-requests/2.25.1'
            },
            'httpMethod': 'GET',
            'protocol': 'HTTP/1.1',
            'requestTime': '10/Oct/2020:19:23:19 +0000',
            'requestTimeEpoch': 1602358999000,
            'authorizer': {},
            'path': '/dev/album',
            'stage': 'dev'
        },
        'stageVariables': {}
    }

    print(f"current dir: {os.getcwd()}")
    ModelFactory.load_spec(api_spec_path="resources/chinook_api.yaml")
    response = lambda_handler(event, None)
    assert response['statusCode'] == 200
    assert json.loads(response['body']) == {"message": "success"}


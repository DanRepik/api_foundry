import boto3
import pulumi_aws as aws
from moto import mock_aws
from unittest.mock import patch

from api_maker.cloudprints.pulumi.lambda_ import PythonFunctionCloudprint  # Replace 'your_module' with the actual module name

@mock_aws
def test_create_lambda_function():
    # Mock the Pulumi stack and project
    with patch('pulumi.get_stack', return_value='test-stack'), \
         patch('pulumi.get_project', return_value='test-project'), \
         patch('boto3.client') as mock_boto_client:
        
        # Mock boto3 client to use LocalStack endpoint
        def mock_client(service_name, *args, **kwargs):
            endpoint_url = kwargs.get('endpoint_url', 'http://localhost:4566')
            return boto3.client(service_name, endpoint_url=endpoint_url)

        mock_boto_client.side_effect = mock_client
        
        # Define parameters for the test
        name = 'test-function'
        hash = 'test-hash'
        archive_location = 'test-archive.zip'
        handler = 'test_handler'
        environment = {'ENV_VAR': 'test'}

        # Create an instance of PythonFunctionCloudprint
        function_resource = PythonFunctionCloudprint(
            name=name,
            hash=hash,
            archive_location=archive_location,
            handler=handler,
            environment=environment
        )

        # Validate the IAM Role creation
        role = function_resource.create_execution_role()
        assert role is not None
        assert role.assume_role_policy is not None

        # Validate the CloudWatch Log Group creation
        log_group = function_resource.create_log_group()
        assert log_group is not None
        assert log_group.retention_in_days == 3

        # Validate the Lambda Function creation
        lambda_function = function_resource.lambda_
        assert lambda_function is not None
        assert lambda_function.handler == handler
        assert lambda_function.runtime == aws.lambda_.Runtime.PYTHON3D12
        assert lambda_function.environment['variables'] == environment

        # Validate the environment variable for secret name is set
        assert 'SECRET_NAME' in lambda_function.environment['variables']

        # Validate the Lambda invoke ARN
        invoke_arn = function_resource.invoke_arn()
        assert invoke_arn is not None

import json

from constructs import Construct

from imports.aws.iam_role import IamRole
from imports.aws.iam_role_policy import IamRolePolicy
from imports.aws.iam_role_policy_attachment import IamRolePolicyAttachment

from ..lib.logger import logger, INFO
from ..lib.common import make_name, make_tags, make_id, make_resource

log = logger(__name__)

class LambdaExecutionRole(Construct):
    role: IamRole

    def __init__(self, scope: Construct, id: str):
        """
        Create an AWS IAM Role for Lambda execution and attach policies to it.

        Args:
            scope (Construct): The scope of the construct.
            id (str): The unique identifier for this construct.
        """
        super().__init__(scope, make_id(scope, id))

        # Create the execution role for Lambda
        self.role = self.create_execution_role(scope, id)
        self.attach_policy = self.attach_policy(scope, id)

        # Attach IAM policies to the role
        self.attach_policy_to_role(
            scope,
            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            "lambdaBasicExecPolicyAtch"
        )

        self.attach_policy_to_role(
            scope,
            "arn:aws:iam::aws:policy/AWSLambdaExecute",
            "lambdaExecPolicyAtch",
        )

    def create_execution_role(self, scope: Construct, id: str) -> IamRole:
        """
        Create an IAM role with an assume role policy for Lambda service.

        Args:
            scope (Construct): The scope of the construct.
            id (str): The unique identifier for this role.

        Returns:
            IamRole: The IAM role created for Lambda execution.
        """
        if log.isEnabledFor(INFO):
            log.info(f"Creating execution_role role_name: {id}")

        # Define the policy that allows Lambda service to assume this role
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["sts:AssumeRole"],
                    "Principal": {
                        "Service": [
                            "lambda.amazonaws.com",
                            "edgelambda.amazonaws.com",
                        ]
                    },
                    "Effect": "Allow"
                }
            ],
        }

        # Create the IAM role with the defined policy
        return IamRole(
            scope,
            make_id(scope, f"{id}-role"),
            name=make_resource(scope, id),
            assume_role_policy=json.dumps(assume_role_policy),
            tags=make_tags(scope, id)
        )

    def attach_policy_to_role(
        self, scope: Construct, policy_arn: str, policy_name: str
    ):
        """
        Attach an IAM policy to the IAM role.

        Args:
            scope (Construct): The scope of the construct.
            policy_arn (str): The ARN of the IAM policy to attach.
            policy_name (str): The name of the policy attachment.
        """
        if log.isEnabledFor(INFO):
            log.info(f"Creating policy attachment: policy_arg: {policy_arn}")
    
        IamRolePolicyAttachment(
            scope,
            make_id(scope, policy_name),
            role=self.role.name,
            policy_arn=policy_arn,
        )

    def attach_policy(self, scope: Construct, id: str) -> IamRolePolicy:
        return IamRolePolicy(
            scope,
            make_id(scope, f"{id}-role-policy"),
            role=self.role.id,
            name=make_resource(scope, f"{id}-role-policy"),
            policy=json.dumps({
                "Version": '2012-10-17',
                "Statement": [
                {
                    "Sid": 'AllowLambdaFunctionInvocation',
                    "Effect": 'Allow',
                    "Action": ['lambda:InvokeFunction'],
                    "Resource": ['*'],
                },
                {
                    # lambda@edge
                    "Sid": "AllowEdgeFunction",
                    "Effect": "Allow",
                    "Action": ["lambda:EnableReplication*", "lambda:GetFunction", "iam:CreateServiceLinkedRole"],
                    "Resource": ["*"],
                },
                {
                    "Sid": 'AllowWsManagementInvocation',
                    "Effect": 'Allow',
                    "Action": ['execute-api:Invoke', 'execute-api:ManageConnections'],
                    "Resource": ['arn:aws:execute-api:*:*:*/*'],
                },
                {
                    "Sid": 'Logs',
                    "Effect": 'Allow',
                    "Action": [
                    'logs:CreateLogGroup',
                    'logs:CreateLogStream',
                    'logs:DescribeLogGroups',
                    'logs:DescribeLogStreams',
                    'logs:PutLogEvents',
                    'logs:GetLogEvents',
                    'logs:FilterLogEvents',
                    ],
                    "Resource": 'arn:aws:logs:*:*:*',
                },
                {
                    "Sid": 'StateMachines',
                    "Effect": 'Allow',
                    "Action": [
                    'states:DescribeStateMachine',
                    'states:StartExecution',
                    'states:SendTaskSuccess',
                    'states:SendTaskFailure',
                    'states:ListExecution',
                    'states:DescribeExecution',
                    'states:DescribeStateMachineForExecution',
                    'states:GetExecutionHistory',
                    'states:SendTaskHeartbeat',
                    'states:GetActivityTask',
                    ],
                    "Resource": 'arn:aws:states:*:*:*:*',
                },
                {
                    "Sid": 'AllowAccessObjectsToS3',
                    "Effect": 'Allow',
                    "Action": ['s3:GetObject', 's3:PutObject', 's3:DeleteObject'],
                    "Resource": '*',
                },
                {
                    "Sid": 'AllowSqsAccess',
                    "Effect": 'Allow',
                    "Action": [
                    'sqs:DeleteMessage',
                    'sqs:GetQueueAttributes',
                    'sqs:GetQueueUrl',
                    'sqs:ReceiveMessage',
                    ],
                    "Resource": '*',
                },
                {
                    "Sid": 'AllowAssumeRole',
                    "Effect": 'Allow',
                    "Action": 'sts:AssumeRole',
                    "Resource": '*',
                },
                {
                    "Sid": 'DDB',
                    "Effect": 'Allow',
                    "Action": [
                    'dynamodb:BatchGet*',
                    'dynamodb:BatchGetItem',
                    'dynamodb:BatchWriteItem',
                    'dynamodb:ConditionCheckItem',
                    'dynamodb:DescribeTable',
                    'dynamodb:GetRecords',
                    'dynamodb:DeleteItem',
                    'dynamodb:DescribeTable',
                    'dynamodb:DescribeStream',
                    'dynamodb:DescribeGlobalTable',
                    'dynamodb:GetShardIterator',
                    'dynamodb:ListStreams',
                    'dynamodb:Query',
                    'dynamodb:PutItem',
                    'dynamodb:GetItem',
                    'dynamodb:UpdateItem',
                    'dynamodb:Scan',
                    ],
                    "Resource": '*',
                },
                {
                    'Sid': 'AllowVPCAccess',
                    'Effect': 'Allow',
                    'Action': [
                    'ec2:CreateNetworkInterface',
                    'ec2:DescribeNetworkInterfaces',
                    'ec2:DeleteNetworkInterface',
                    'ec2:AssignPrivateIpAddresses',
                    'ec2:UnassignPrivateIpAddresses'
                    ],
                    'Resource': '*'
                },
                {
                    "Sid": 'TextractAccess',
                    "Effect": 'Allow',
                    "Action": 'textract:*',
                    "Resource": '*',
                },
                {
                    "Sid": 'secretsmanager',
                    "Effect": 'Allow',
                    "Action": 'secretsmanager:GetSecretValue',
                    "Resource": ['*'],
                },
                {
                    "Sid": 'sns',
                    "Effect": 'Allow',
                    "Action": 'sns:*',
                    "Resource": ['*'],
                },
                {
                    "Sid": 'ssm',
                    "Effect": 'Allow',
                    "Action": [
                    'ssm:GetParametersByPath',
                    'ssm:GetParameter',
                    'kms:Decrypt'
                    ],
                    "Resource": ['*'],
                },
                ]
            })
        )

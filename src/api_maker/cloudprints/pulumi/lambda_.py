from zipfile import ZipFile

import pulumi
import pulumi_aws as aws

from api_maker.utils.logger import logger, DEBUG

log = logger(__name__)


class PythonFunctionCloudprint(pulumi.ComponentResource):
    name: str
    handler: str
    lambda_: aws.lambda_.Function

    def __init__(self, name, hash: str, archive_location: str, handler: str, environment = None, opts=None):
        self.name = name
        self.handler = handler
        self.create_lambda_function(hash, archive_location, environment)

    def create_execution_role(self) -> aws.iam.Role:
        log.debug("creating execution role")
        assume_role = aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    effect="Allow",
                    principals=[
                        aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                            type="Service",
                            identifiers=["lambda.amazonaws.com"],
                        )
                    ],
                    actions=["sts:AssumeRole"],
                )
            ]
        )

        return aws.iam.Role(
            f"{self.name}-lambda-execution",
            name=f"{pulumi.get_project()}-{self.name}-lambda-execution",
            assume_role_policy=assume_role.json,
        )

    def create_log_group(self) -> aws.cloudwatch.LogGroup:
        return aws.cloudwatch.LogGroup(
            f"{self.name}-log-group",
            name=f"{pulumi.get_project()}-{self.name}",
            retention_in_days=3,
        )

    def invoke_arn(self) -> pulumi.Output[str]:
        return self.lambda_.invoke_arn

    def create_lambda_function(self, hash: str, archive_location: str, environment):
        log.debug("creating lambda function")
        self.lambda_ = aws.lambda_.Function(
            f"{self.name}-lambda",
            code=pulumi.FileArchive(archive_location),
            name=f"{pulumi.get_project()}-{self.name}",
            role=self.create_execution_role().arn,
            logging_config={"log_format": "JSON", "log_group": self.create_log_group()},
            handler=self.handler,
            source_code_hash=hash,
            runtime=aws.lambda_.Runtime.PYTHON3D12,
            environment=aws.lambda_.FunctionEnvironmentArgs(variables=environment),
        )

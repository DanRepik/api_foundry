import pulumi
import pulumi_aws as aws
from api_foundry.utils.logger import logger

log = logger(__name__)


class PythonFunctionCloudprint(pulumi.ComponentResource):
    name: str
    handler: str
    lambda_: aws.lambda_.Function

    def __init__(
        self,
        name,
        hash: str,
        archive_location: str,
        handler: str,
        environment=None,
        opts=None,
    ):
        super().__init__("custom:resource:PythonFunctionCloudprint", name, {}, opts)
        self.name = name
        self.handler = handler
        self.environment = environment or {}
        self.create_lambda_function(hash, archive_location)
        self.register_outputs({})

    def create_execution_role(self) -> aws.iam.Role:
        log.debug("creating execution role")
        assume_role_policy = aws.iam.get_policy_document(
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

        role = aws.iam.Role(
            f"{self.name}-lambda-execution",
            assume_role_policy=assume_role_policy.json,
        )

        aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    effect="Allow",
                    actions=[
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    resources=["*"],  # Allow access to all secrets and logs
                )
            ]
        )

        """
        aws.iam.RolePolicy(
            f"{self.name}-lambda-policy",
            role=role.id,
            policy=policy_document.json,
            opts=pulumi.ResourceOptions(depends_on=[role])
        )
        """

        return role

    def create_log_group(self) -> aws.cloudwatch.LogGroup:
        log_group = aws.cloudwatch.LogGroup(
            f"{self.name}-log-group",
            name=f"/aws/lambda/{pulumi.get_project()}-{self.name}",
            retention_in_days=3,
        )
        return log_group

    def invoke_arn(self) -> pulumi.Output[str]:
        return self.lambda_.invoke_arn

    def create_lambda_function(self, hash: str, archive_location: str):
        log.debug("creating lambda function")

        log_group = self.create_log_group()

        execution_role = self.create_execution_role()

        self.lambda_ = aws.lambda_.Function(
            f"{self.name}-lambda",
            code=pulumi.FileArchive(archive_location),
            name=f"{pulumi.get_project()}-{self.name}",
            role=execution_role.arn,
            handler=self.handler,
            source_code_hash=hash,
            runtime=aws.lambda_.Runtime.PYTHON3D9,
            environment=aws.lambda_.FunctionEnvironmentArgs(variables=self.environment),
            opts=pulumi.ResourceOptions(depends_on=[execution_role, log_group]),
        )

from aws_cdk import (
    aws_iam as iam,
    core
)

class LambdaExecutionRole(core.Construct):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a role for the Lambda function
        self.lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )

        # Output the ARN of the Lambda execution role
        core.CfnOutput(
            self, "LambdaExecutionRoleArn",
            value=self.lambda_role.role_arn,
            export_name="LambdaExecutionRoleArn"
        )


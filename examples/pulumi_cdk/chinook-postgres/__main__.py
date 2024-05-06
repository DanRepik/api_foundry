import os
import shutil
import subprocess
import sys
from zipfile import ZipFile

import pulumi
import pulumi_aws as aws

from api_maker.utils.logger import logger, DEBUG

log = logger(__name__)


class LambdaDeployment:
    def __init__(self, id: str, requirements: list[str], working_dir: str):
        base_dir = os.path.join(working_dir, f"{id}-lambda")
        self.staging = os.path.join(base_dir, "staging")
        if not os.path.exists(self.staging):
            os.makedirs(self.staging)
        self.libs = os.path.join(base_dir, "staging")
        if not os.path.exists(self.libs):
            os.makedirs(self.libs)

        if requirements:
            self.write_requirements(requirements)

        self.build_archive()

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

        self.iam_for_lambda = aws.iam.Role(
            f"{id}-lambda-execution",
            name="iam_for_lambda",
            assume_role_policy=assume_role.json,
        )

    def build_archive(self, requirements: list[str]):
        # Define the Lambda function code
        lambda_code = """
    def lambda_handler(event, context):
        # Your Lambda function code here
        return 'Hello from Lambda!'
    """

        # Write the Lambda function code to a file
        with open("lambda_function.py", "w") as f:
            f.write(lambda_code)

        # Create a ZIP archive of the Lambda function code and requirements
        with ZipFile("lambda_function.zip", "w") as zipf:
            zipf.write("lambda_function.py")
            zipf.write("requirements.txt")
            for folder_name, _, filenames in os.walk("requests"):
                for filename in filenames:
                    file_path = os.path.join(folder_name, filename)
                    zipf.write(file_path, os.path.relpath(file_path, "."))

        # Clean up
        shutil.rmtree("requests")
        os.remove("lambda_function.py")
        os.remove("requirements.txt")

    def write_requirements(self, requirements: list[str]):
        if log.isEnabledFor(DEBUG):
            log.debug("writing requirements")

        with open(f"{self.staging}/requirements.txt", "w") as f:
            for requirement in requirements:
                f.write(requirement + "\n")

    def install_requirements(self):
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--target",
                self.libs,
                "--platform",
                "manylinux2010_x86_64",
                "--implementation",
                "cp",
                "--only-binary=:all:",
                "--upgrade",
                "--python-version",
                "3.9",
                "-r",
                f"{self.staging}/requirements.txt",
            ]
        )


lambda_deployment = LambdaDeployment(
    id="api-maker",
    requirements=[
        "oracledb~=2.1",
        "psycopg2-binary~=2.9",
        "pyyaml~=6.0",
        "-e /Users/clydedanielrepik/workspace/api_maker",
    ],
    working_dir="temp",
)

"""
lambda_ = archive.get_file(type="zip",
    source_file="lambda.js",
    output_path="lambda_function_payload.zip")

test_lambda = aws.lambda_.Function("test_lambda",
    code=pulumi.FileArchive("lambda_function_payload.zip"),
    name="lambda_function_name",
    role=iam_for_lambda.arn,
    handler="index.test",
    source_code_hash=lambda_.output_base64sha256,
    runtime=aws.lambda_.Runtime.NODE_JS18D_X,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "foo": "bar",
        },
    ))

"""

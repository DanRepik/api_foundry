import json
import os
import shutil
import subprocess
import sys
from zipfile import ZipFile

import pulumi
import pulumi_aws as aws

from api_maker.utils.logger import logger, DEBUG
from hash_comparator import HashComparator

log = logger(__name__)


class LambdaDeployment:
    def __init__(
        self,
        id: str,
        *,
        sources: dict[str, str],
        requirements: list[str],
        environment: dict,
        working_dir: str,
    ):
        self._id = id
        self._sources = sources
        self._requirements = requirements
        self._environment = environment
        self._working_dir = working_dir

        self.prepare()

        hash_comparator = HashComparator()
        hash = hash_comparator.hash_folder(self._staging)
        log.debug(f"hash: {hash}")
        log.debug(f"old_hash: {hash_comparator.read(self._base_dir)}")
        if hash_comparator.read(self._base_dir) != hash:
            log.debug("hash comparison matches, deployment skipped")
            self.install_requirements()
            self.build_archive()

        self.create_execution_role()
        self.create_lambda_function(hash)
        hash_comparator.write(hash, self._base_dir)

    def create_execution_role(self):
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

        self.iam_for_lambda = aws.iam.Role(
            f"{self._id}-lambda-execution",
            name="iam_for_lambda",
            assume_role_policy=assume_role.json,
        )

    def create_lambda_function(self, hash):
        log.debug("creating lambda function")
        self._lambda = aws.lambda_.Function(
            f"{self._id}-lambda",
            code=pulumi.FileArchive(self._archive_name),
            name=f"{self._id}-lambda",
            role=self.iam_for_lambda.arn,
            handler="index.test",
            source_code_hash=hash,
            runtime=aws.lambda_.Runtime.PYTHON3D12,
            environment=aws.lambda_.FunctionEnvironmentArgs(
                variables=self._environment
            ),
        )

    def prepare(self):
        self._base_dir = os.path.join(self._working_dir, f"{self._id}-lambda")
        self._staging = os.path.join(self._base_dir, "staging")
        if os.path.exists(self._staging):
            self.clean_folder(self._staging)
        else:
            os.makedirs(self._staging)

        self._libs = os.path.join(self._base_dir, "libs")
        if os.path.exists(self._libs):
            self.clean_folder(self._libs)
        else:
            os.makedirs(self._libs)

        self._archive_name = os.path.join(self._base_dir, f"{self._id}.zip")
        self.install_sources()
        self.write_requirements()

    def build_archive(self):
        log.info(f"building archive: {self._id}")
        # Create a ZIP archive of the Lambda function code and requirements
        with ZipFile(self._archive_name, "w") as zipf:
            for top_folder in [self._staging, self._libs]:
                for folder_name, _, filenames in os.walk(top_folder):
                    for filename in filenames:
                        file_path = os.path.join(folder_name, filename)
                        archive_path = os.path.join(
                            os.path.relpath(folder_name, top_folder), filename
                        )
                        zipf.write(file_path, archive_path)

    def install_sources(self):
        log.info(f"installing resources: {self._id}")
        if self._sources is None:
            return
        for destination, source_folder in self._sources.items():
            # Copy the entire contents of the source folder
            # to the destination folder
            destination_folder = os.path.join(self._staging, destination)
            log.info(
                f"source: {source_folder}, destination: {destination_folder}"
            )
            shutil.copytree(source_folder, destination_folder)
            log.info(
                f"Folder copied from {source_folder} to {destination_folder}"
            )

    def write_requirements(self):
        if log.isEnabledFor(DEBUG):
            log.debug("writing requirements")

        with open(f"{self._staging}/requirements.txt", "w") as f:
            for requirement in self._requirements:
                f.write(requirement + "\n")

    def install_requirements(self):
        log.info(f"installing packages {self._id}")
        self.clean_folder(self._libs)
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--target",
                self._libs,
                "--platform",
                "manylinux2010_x86_64",
                "--implementation",
                "cp",
                "--only-binary=:all:",
                "--upgrade",
                "--python-version",
                "3.9",
                "-r",
                os.path.join(self._staging, "requirements.txt"),
            ]
        )

    def clean_folder(self, folder_path):
        """
        Remove all files and folders from the specified folder.

        Args:
            folder_path (str): Path to the folder from which to
              remove files and folders.

        Returns:
            None
        """
        log.info(f"Cleaning folder: {folder_path}")
        # Remove all files and subdirectories in the specified folder
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        log.info(f"All files and folders removed from {folder_path}")


api_maker_source = "/Users/clydedanielrepik/workspace/api_maker/src/api_maker"
lambda_deployment = LambdaDeployment(
    id="api-maker",
    sources={"api_maker": api_maker_source},
    requirements=[
        "oracledb~=2.1",
        "psycopg2-binary~=2.9",
        "pyyaml~=6.0",
        "-e /Users/clydedanielrepik/workspace/api_maker",
    ],
    environment={
        "SECRETS": json.dumps({"chinook-postgres": "postgres/chinook"})
    },
    working_dir="temp",
)

"""
lambda_ = archive.get_file(type="zip",
    source_file="lambda.js",
    output_path="lambda_function_payload.zip")


"""

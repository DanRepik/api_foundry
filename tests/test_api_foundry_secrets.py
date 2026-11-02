"""
APIFoundry must accept ``secrets`` as a ``pulumi.Output[str]``.

Previously ``json.loads`` was called on the Output directly, raising an
uncaught TypeError at plan time. The GetSecretValue grant must name the
resolved secret ARN (not ``*``) once the Output resolves.

Runs under pulumi's mock runtime. ``cloud_foundry.rest_api`` is stubbed;
the real ``python_function`` is used so the function role policy is built,
with the Lambda archive step stubbed out.
"""

import json

import pulumi
import pytest

import cloud_foundry
from api_foundry.iac.pulumi.api_foundry import APIFoundry

MINIMAL_SPEC = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
components:
  schemas:
    album:
      type: object
      x-af-database: chinook
      properties:
        album_id:
          type: integer
          x-af-primary-key: auto
        title:
          type: string
"""

SECRET_ARN = (
    "arn:aws:secretsmanager:us-east-1:123456789012:secret:chinook-db-AbCdEf"
)


class FakeRestAPI:
    domain = "test.example.com"


@pytest.fixture
def role_policies():
    policies = {}

    class Mocks(pulumi.runtime.Mocks):
        def new_resource(self, args):
            if args.typ == "aws:iam/rolePolicy:RolePolicy":
                policies[args.name] = args.inputs.get("policy")
            outputs = dict(args.inputs)
            outputs.setdefault("arn", f"arn:aws:mock:::{args.name}")
            return [args.name + "_id", outputs]

        def call(self, args):
            if args.token == "aws:iam/getPolicyDocument:getPolicyDocument":
                statements = [
                    {
                        "Effect": s.get("effect", "Allow"),
                        "Action": s.get("actions", []),
                        "Resource": s.get("resources", []),
                    }
                    for s in args.args.get("statements", [])
                ]
                return {
                    "json": json.dumps(
                        {"Version": "2012-10-17", "Statement": statements}
                    )
                }
            return {}

    pulumi.runtime.set_mocks(Mocks(), preview=False)
    return policies


@pytest.mark.unit
def test_output_secrets_grant_names_resolved_arn(role_policies, monkeypatch):
    monkeypatch.setattr(
        cloud_foundry, "rest_api", lambda *args, **kwargs: FakeRestAPI()
    )

    @pulumi.runtime.test
    def program():
        secrets = pulumi.Output.json_dumps(
            {"chinook": pulumi.Output.from_input(SECRET_ARN)}
        )
        api = APIFoundry("test-api", api_spec=MINIMAL_SPEC, secrets=secrets)
        return api.api_function.arn

    # pulumi.runtime.test waits for all outstanding resource registrations,
    # so the role policy has been recorded once program() returns.
    program()

    policy = role_policies["test-api-role-policy"]
    statements = json.loads(policy)["Statement"]
    secret_statements = [
        s for s in statements if "secretsmanager:GetSecretValue" in s["Action"]
    ]
    assert len(secret_statements) == 1, statements
    assert secret_statements[0]["Resource"] == [SECRET_ARN]

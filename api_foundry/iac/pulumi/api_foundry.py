import os
import json
import yaml
import boto3
from typing import Optional, Union
from pulumi import ComponentResource

import pulumi
import cloud_foundry

from api_foundry.iac.gateway_spec import APISpecEditor
from api_foundry.utils.model_factory import ModelFactory
from cloud_foundry import logger

log = logger(__name__)


def is_valid_openapi_spec(spec_dict: dict) -> bool:
    return (
        isinstance(spec_dict, dict)
        and "openapi" in spec_dict
        and isinstance(spec_dict["openapi"], str)
    )


def load_api_spec(api_spec: Union[str, list[str]]) -> dict:
    """
    Load one or more OpenAPI specs from files, directories,
    S3, or inline YAML.

        Accepts:
            - File path(s)
            - Directory path(s): loads all .yaml/.yml files (sorted)
            - S3 URL(s): s3://bucket/key or s3://bucket/prefix/
            - Inline YAML string with an OpenAPI document

        Returns a shallow-merged spec dict; later documents win on conflicts.
    """

    def _is_s3_url(s: str) -> bool:
        return isinstance(s, str) and s.startswith("s3://")

    def _gather_inputs(specs: Union[str, list[str]]) -> list[Union[str, dict]]:
        items = [specs] if isinstance(specs, str) else list(specs or [])
        inputs: list[Union[str, dict]] = []
        for spec in items:
            if not isinstance(spec, str):
                raise TypeError("api_spec entries must be strings")

            # Local file
            if os.path.isfile(spec):
                inputs.append(spec)
                continue

            # Local directory: include .yaml/.yml files only
            if os.path.isdir(spec):
                files = [
                    os.path.join(spec, f)
                    for f in os.listdir(spec)
                    if f.endswith((".yaml", ".yml"))
                ]
                inputs.extend(sorted(files))
                continue

            # S3 file or prefix
            if _is_s3_url(spec):
                bucket, key = spec[5:].split("/", 1)
                if key.endswith("/"):
                    s3 = boto3.client("s3")
                    resp = s3.list_objects_v2(Bucket=bucket, Prefix=key)
                    contents = resp.get("Contents", [])
                    keys = [
                        o["Key"]
                        for o in contents
                        if o["Key"].endswith((".yaml", ".yml"))
                    ]
                    inputs.extend([f"s3://{bucket}/{k}" for k in sorted(keys)])
                else:
                    inputs.append(spec)
                continue

            # Inline YAML
            try:
                as_yaml = yaml.safe_load(spec)
            except yaml.YAMLError as exc:  # not YAML
                raise ValueError(f"Invalid OpenAPI spec source: {spec}") from exc

            if is_valid_openapi_spec(as_yaml):
                inputs.append(as_yaml)
            else:
                raise ValueError(f"Invalid OpenAPI spec provided: {spec}")

        return inputs

    merged: dict = {}
    for source in _gather_inputs(api_spec):
        if isinstance(source, dict):
            spec_dict = source
        elif _is_s3_url(source):
            bucket, key = source[5:].split("/", 1)
            s3 = boto3.client("s3")
            obj = s3.get_object(Bucket=bucket, Key=key)
            spec_dict = yaml.safe_load(obj["Body"].read().decode("utf-8"))
        else:
            with open(source, "r", encoding="utf-8") as f:
                spec_dict = yaml.safe_load(f)

        if not is_valid_openapi_spec(spec_dict):
            raise ValueError(f"Invalid OpenAPI spec found in: {source}")

        merged.update(spec_dict)

    return merged


class APIFoundry(ComponentResource):
    api_spec_editor: APISpecEditor

    def __init__(
        self,
        name,
        *,
        api_spec: Union[str, list[str]],
        batch_path: Optional[str] = None,
        secrets: Optional[str] = None,
        environment: Optional[dict[str, Union[str, pulumi.Output[str]]]] = None,
        integrations: Optional[list[dict]] = None,
        token_validators: Optional[list[dict]] = None,
        policy_statements: Optional[list] = None,
        vpc_config: Optional[dict] = None,
        export_api: Optional[str] = None,
        opts=None,
    ):
        super().__init__("cloud_foundry:apigw:APIFoundry", name, None, opts)

        api_spec_dict = load_api_spec(api_spec)
        config_defaults = api_spec_dict.get("x-af-configuration", {})

        secrets = secrets or config_defaults.get("secrets", "")
        env_vars = environment or config_defaults.get(
            "environment", {}
        )  # type: dict[str, Union[str, pulumi.Output[str]]]
        integrations = integrations or config_defaults.get("integrations", [])
        token_validators = token_validators or config_defaults.get(
            "token_validators", []
        )
        policy_statements = policy_statements or config_defaults.get(
            "policy_statements", []
        )
        vpc_config = vpc_config or config_defaults.get("vpc_config", {})

        env_vars["SECRETS"] = secrets
        requirements = []

        # Grant read access to referenced secrets (single broad stmt)
        if json.loads(secrets):
            policy_statements.append(
                {
                    "Effect": "Allow",
                    "Actions": ["secretsmanager:GetSecretValue"],
                    "Resources": ["*"],
                }
            )

            requirements.extend(
                ["psycopg2-binary", "pyyaml", "../api_foundry_query_engine"]
            )
        if env_vars.get("JWKS_HOST"):
            requirements.extend(["PyJWT", "cryptography", "requests"])

        self.api_function = cloud_foundry.python_function(
            name=name,
            environment=env_vars,
            handler="api_foundry_query_engine.lambda_handler.handler",
            sources={
                "api_spec.yaml": yaml.safe_dump(
                    ModelFactory(api_spec_dict).get_config_output()
                ),
            },
            requirements=requirements,
            policy_statements=policy_statements,
            vpc_config=vpc_config,
        )

        gateway_spec = APISpecEditor(
            open_api_spec=api_spec_dict,
            function=self.api_function,
            batch_path=batch_path,
        )

        # Merge gateway_spec.integrations with user-provided integrations
        specification = gateway_spec.rest_api_spec()
        merged_integrations = (integrations or []) + (gateway_spec.integrations or [])

        self.rest_api = cloud_foundry.rest_api(
            name,
            specification=[specification],
            integrations=merged_integrations,
            token_validators=token_validators or [],
            export_api=export_api,
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.domain = self.rest_api.domain

        self.register_outputs({f"{name}_domain": self.domain})

    def integrations(self) -> list[dict]:
        return self.api_spec_editor.integrations

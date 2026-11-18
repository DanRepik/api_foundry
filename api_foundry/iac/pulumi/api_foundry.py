import os
import re
import json
import yaml
import boto3
from typing import Optional, Union
from pulumi import ComponentResource

import pulumi
import pulumi_aws as aws
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


# Requests per second (steady rate) and burst API Gateway lets through, across
# all callers, for every route of the stage unless the spec's x-af-throttle says
# otherwise. Far below the account default (10,000/5,000), so an open route
# can't run up the database bill.
DEFAULT_THROTTLE = {"rate": 100, "burst": 200}
_METHODS = ("get", "put", "post", "delete", "patch")


def _throttle(value, where: str) -> dict:
    """An x-af-throttle checked: {rate: positive number, burst: positive integer}."""
    if not isinstance(value, dict) or set(value) != {"rate", "burst"}:
        raise ValueError(
            f"{where}: x-af-throttle needs rate and burst, e.g. {{rate: 10, burst: 20}}"
        )
    rate, burst = value["rate"], value["burst"]
    if (
        isinstance(rate, bool)
        or not isinstance(rate, (int, float))
        or rate <= 0
        or isinstance(burst, bool)
        or not isinstance(burst, int)
        or burst <= 0
    ):
        raise ValueError(
            f"{where}: x-af-throttle rate must be a positive number and burst a "
            f"positive integer, not {value!r}"
        )
    return {"rate": float(rate), "burst": burst}


def throttle_limits(spec: dict, path_prefix: Optional[str] = None) -> dict[str, dict]:
    """API Gateway method settings paths and their limits.

    ``*/*`` is the whole stage: the spec's top-level ``x-af-throttle``, else
    DEFAULT_THROTTLE. Each path operation with its own ``x-af-throttle`` gets
    ``{resource path}/{METHOD}``: the resource path with ``path_prefix`` (as
    cloud_foundry prefixes it) and without its leading "/", the form the AWS
    provider's ``method_path`` takes. The provider stores and looks up the
    setting under exactly this key, so a "~1"-encoded path deploys without
    error and matches no resource.
    """
    limits = {"*/*": _throttle(spec.get("x-af-throttle", DEFAULT_THROTTLE), "spec")}
    for path, item in (spec.get("paths") or {}).items():
        for method in _METHODS:
            operation = item.get(method) if isinstance(item, dict) else None
            if not isinstance(operation, dict) or "x-af-throttle" not in operation:
                continue
            resource = (
                f"{path_prefix.rstrip('/')}/{path.lstrip('/')}" if path_prefix else path
            )
            limits[f"{resource.lstrip('/')}/{method.upper()}"] = _throttle(
                operation["x-af-throttle"], f"{method.upper()} {path}"
            )
    return limits


class APIFoundry(ComponentResource):
    api_spec_editor: APISpecEditor

    def __init__(
        self,
        name,
        *,
        api_spec: Union[str, list[str]],
        batch_path: Optional[str] = None,
        secrets: Optional[Union[str, pulumi.Output[str]]] = None,
        path_prefix: Optional[str] = None,
        environment: Optional[dict[str, Union[str, pulumi.Output[str]]]] = None,
        integrations: Optional[list[dict]] = None,
        token_validators: Optional[list[dict]] = None,
        timeout_seconds: Optional[int] = None,
        policy_statements: Optional[list] = None,
        vpc_config: Optional[dict] = None,
        hosted_zone_id: Optional[str] = None,
        subdomain: Optional[str] = None,
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

        # Grant read access to referenced secrets
        if secrets:
            if isinstance(secrets, pulumi.Output):
                # Resolve the ARNs at deploy time rather than widening the
                # grant to "*". The statement list is resolved as a whole
                # before it reaches cloud_foundry (see below).
                policy_statements.append(
                    {
                        "Effect": "Allow",
                        "Actions": ["secretsmanager:GetSecretValue"],
                        "Resources": secrets.apply(
                            lambda s: list(json.loads(s).values())
                        ),
                    }
                )
            else:
                try:
                    secret_arns = list(json.loads(secrets).values())
                    policy_statements.append(
                        {
                            "Effect": "Allow",
                            "Actions": ["secretsmanager:GetSecretValue"],
                            "Resources": secret_arns,
                        }
                    )
                except (json.JSONDecodeError, AttributeError):
                    # Invalid JSON: fall back to a broad policy
                    policy_statements.append(
                        {
                            "Effect": "Allow",
                            "Actions": ["secretsmanager:GetSecretValue"],
                            "Resources": "*",
                        }
                    )

            requirements.extend(
                [
                    "psycopg2-binary",
                    "pyyaml",
                    "api_foundry_query_engine",
                ]
            )

        # Configure Lambda-based token validation if validators are provided
        if token_validators:
            # Get the first validator function (primary validator)
            primary_validator = token_validators[0]
            validator_function = primary_validator.get("function")

            if validator_function:
                # Check if validator_function has 'arn' attribute
                # (Pulumi Output)
                if hasattr(validator_function, "arn"):
                    # Store the ARN for the query engine to invoke
                    env_vars["TOKEN_VALIDATOR_LAMBDA_ARN"] = validator_function.arn

                    # Grant invoke permission for the query lambda
                    policy_statements.append(
                        {
                            "Effect": "Allow",
                            "Actions": ["lambda:InvokeFunction"],
                            "Resources": [validator_function.arn],
                        }
                    )
                    log.info("Configured Lambda token validator for query engine")

        if env_vars.get("JWKS_HOST"):
            requirements.extend(["PyJWT", "cryptography", "requests"])

        if isinstance(secrets, pulumi.Output):
            # cloud_foundry builds the role policy from plain statements, but
            # accepts the statement list itself as an Output. Resolve the
            # list (including Outputs nested in Resources) as one Output.
            policy_statements = pulumi.Output.from_input(policy_statements)

        self.api_function = cloud_foundry.python_function(
            name=name,
            environment=env_vars,
            runtime="python3.12",
            handler="api_foundry_query_engine.lambda_handler.handler",
            sources={
                "api_spec.yaml": yaml.safe_dump(
                    ModelFactory(api_spec_dict).get_config_output()
                ),
            },
            requirements=requirements,
            timeout=timeout_seconds or 30,
            policy_statements=policy_statements,
            vpc_config=vpc_config,
        )

        gateway_spec = APISpecEditor(
            open_api_spec=api_spec_dict,
            function=self.api_function,
            batch_path=batch_path,
            token_validators=token_validators,
        )
        self.api_spec_editor = gateway_spec

        # Merge gateway_spec.integrations with user-provided integrations
        specification = gateway_spec.rest_api_spec()
        merged_integrations = (integrations or []) + (gateway_spec.integrations or [])

        self.rest_api = cloud_foundry.rest_api(
            name,
            specification=[specification],
            integrations=merged_integrations,
            token_validators=token_validators or [],
            export_api=export_api,
            path_prefix=path_prefix,
            hosted_zone_id=hosted_zone_id,
            subdomain=subdomain,
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.domain = self.rest_api.domain

        # Throttling, one method settings resource per limit. Each updates
        # the same stage, and concurrent stage updates conflict, so each
        # waits for the one before.
        previous = None
        for method_path, limit in throttle_limits(api_spec_dict, path_prefix).items():
            slug = re.sub(r"[^A-Za-z0-9]+", "-", method_path).strip("-") or "stage"
            previous = aws.apigateway.MethodSettings(
                f"{name}-limit-{slug}",
                rest_api=self.rest_api.rest_api_id,
                stage_name=self.rest_api.stage_name,
                method_path=method_path,
                settings=aws.apigateway.MethodSettingsSettingsArgs(
                    throttling_rate_limit=limit["rate"],
                    throttling_burst_limit=limit["burst"],
                ),
                opts=pulumi.ResourceOptions(
                    parent=self, depends_on=[previous] if previous else None
                ),
            )

        self.register_outputs({f"{name}_domain": self.domain})

    def integrations(self) -> list[dict]:
        return self.api_spec_editor.integrations

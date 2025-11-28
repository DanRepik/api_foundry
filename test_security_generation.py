#!/usr/bin/env python3
"""Test security attribute generation in gateway_spec.py

This test verifies that APISpecEditor:
1. Extracts validator names from x-af-permissions provider keys
2. Applies security: [{validator_name: []}] to generated operations

Note: APISpecEditor does NOT build components.securitySchemes - that's
handled by cloud_foundry.rest_api() which receives the token_validators.
"""

import yaml
from api_foundry.iac.gateway_spec import APISpecEditor


class MockFunction:
    """Mock Lambda function for testing."""

    def __init__(self, name="test-function"):
        self.name = name
        self.invoke_arn = f"arn:aws:lambda:us-east-1:123456789012:function:{name}"
        self.url = f"https://{name}.lambda-url.us-east-1.on.aws/"


def test_security_attribute_generation():
    """Test that operations get security attributes from x-af-permissions."""

    spec = {
        "openapi": "3.1.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "components": {
            "schemas": {
                "users": {
                    "type": "object",
                    "x-af-database": "test_db",
                    "x-af-permissions": {"default": {"read": {"user": ".*"}}},
                    "properties": {
                        "id": {"type": "integer", "x-af-primary-key": "auto"},
                        "name": {"type": "string"},
                    },
                }
            }
        },
    }

    mock_validator = MockFunction("test-validator")
    token_validators = [
        {"type": "token_validator", "name": "default", "function": mock_validator}
    ]

    editor = APISpecEditor(
        open_api_spec=spec,
        function=MockFunction("api-handler"),
        token_validators=token_validators,
    )

    result_yaml = editor.rest_api_spec()
    result = yaml.safe_load(result_yaml)

    print("\n=== Generated OpenAPI Spec ===")
    print(yaml.dump(result, default_flow_style=False))

    # Verify operations have security attribute
    assert "paths" in result
    assert "/users" in result["paths"]

    get_operation = result["paths"]["/users"].get("get")
    assert get_operation is not None
    assert "security" in get_operation
    assert get_operation["security"] == [{"default": []}]

    print("\n✓ Operations have security attribute with validator name")

    # Note: We do NOT check for components.securitySchemes here
    # That's built by cloud_foundry.rest_api(), not APISpecEditor

    print("\n=== Test passed! ===")


def test_x_af_permissions_validators():
    """Test validators extracted from x-af-permissions provider keys."""

    spec = {
        "openapi": "3.1.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "components": {
            "schemas": {
                "products": {
                    "type": "object",
                    "x-af-database": "test_db",
                    "x-af-permissions": {
                        "my-auth": {  # Validator name from provider key
                            "read": {"user": ".*"}
                        }
                    },
                    "properties": {
                        "id": {"type": "integer", "x-af-primary-key": "auto"},
                        "name": {"type": "string"},
                    },
                }
            }
        },
    }

    mock_validator = MockFunction("my-auth-validator")
    token_validators = [
        {"type": "token_validator", "name": "my-auth", "function": mock_validator}
    ]

    editor = APISpecEditor(
        open_api_spec=spec,
        function=MockFunction("api-handler"),
        token_validators=token_validators,
    )

    result_yaml = editor.rest_api_spec()
    result = yaml.safe_load(result_yaml)

    print("\n=== Generated Spec (custom validator) ===")
    print(yaml.dump(result, default_flow_style=False))

    # Verify operations use the custom validator name
    get_operation = result["paths"]["/products"].get("get")
    assert get_operation is not None
    assert "security" in get_operation
    assert get_operation["security"] == [{"my-auth": []}]

    print("\n✓ x-af-permissions provider keys work correctly")
    print("\n=== Test passed! ===")


if __name__ == "__main__":
    test_security_attribute_generation()
    test_x_af_permissions_validators()
    print("\n🎉 All tests passed!")

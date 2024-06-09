import pytest
import json
from api_maker.utils.model_factory import ModelFactory, SchemaObject
from api_maker.utils.logger import logger

from api_maker.iac.gateway_spec import GatewaySpec

log = logger(__name__)


@pytest.fixture(scope="module")
def setup_model_factory():
    api_spec = {
        "openapi": "3.0.0",
        "components": {
            "schemas": {
                "TestSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "x-am-primary-key": True},
                        "name": {
                            "type": "string",
                            "x-am-column-name": "name",
                            "x-am-column-type": "string",
                            "minLength": 1,
                            "maxLength": 255,
                            "pattern": "^[a-zA-Z]+$",
                        },
                    },
                }
            }
        },
    }
    ModelFactory.set_spec(api_spec)


def test_gateway_spec_initialization(setup_model_factory):
    function_name = "test_function"
    function_invoke_arn = "arn:aws:lambda:us-east-1:000000000000:function:test_function"
    gateway_spec = GatewaySpec(
        function_name=function_name,
        function_invoke_arn=function_invoke_arn,
        enable_cors=True,
    )

    assert gateway_spec.function_name == function_name
    assert gateway_spec.function_invoke_arn == function_invoke_arn
    assert "paths" in gateway_spec.api_spec
    assert "components" in gateway_spec.api_spec
    assert "schemas" in gateway_spec.api_spec["components"]
    assert "testschema" in gateway_spec.api_spec["components"]["schemas"]


def test_gateway_spec_as_json(setup_model_factory):
    function_name = "test_function"
    function_invoke_arn = "arn:aws:lambda:us-east-1:000000000000:function:test_function"
    gateway_spec = GatewaySpec(
        function_name=function_name,
        function_invoke_arn=function_invoke_arn,
        enable_cors=True,
    )

    api_spec_json = gateway_spec.as_json()
    assert isinstance(api_spec_json, str)
    assert "testschema" in api_spec_json


def test_gateway_spec_as_yaml(setup_model_factory):
    function_name = "test_function"
    function_invoke_arn = "arn:aws:lambda:us-east-1:000000000000:function:test_function"
    gateway_spec = GatewaySpec(
        function_name=function_name,
        function_invoke_arn=function_invoke_arn,
        enable_cors=True,
    )

    api_spec_yaml = gateway_spec.as_yaml()
    assert isinstance(api_spec_yaml, str)
    assert "testschema" in api_spec_yaml


def test_gateway_spec_operations(setup_model_factory):
    function_name = "test_function"
    function_invoke_arn = "arn:aws:lambda:us-east-1:000000000000:function:test_function"
    gateway_spec = GatewaySpec(
        function_name=function_name,
        function_invoke_arn=function_invoke_arn,
        enable_cors=True,
    )

    schema_name = "TestSchema"
    schema_object = ModelFactory.get_schema_object(schema_name.lower())
    gateway_spec.generate_crud_operations(schema_name, schema_object)

    assert f"/{schema_name.lower()}" in gateway_spec.api_spec["paths"]
    assert "get" in gateway_spec.api_spec["paths"][f"/{schema_name.lower()}"]
    assert "post" in gateway_spec.api_spec["paths"][f"/{schema_name.lower()}"]


if __name__ == "__main__":
    pytest.main()

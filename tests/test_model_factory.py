import os
import yaml
import boto3
import pytest
from unittest.mock import patch, MagicMock
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.utils.model_factory import (
    ModelFactory,
    SchemaObject,
    SchemaObjectProperty,
    OpenAPIElement,
)  # Replace 'your_module' with the actual module name

log = logger(__name__)


def test_set_spec():
    # Mock the file content of api_spec.yaml
    ModelFactory.set_spec(
        {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "TestSchema": {
                        "type": "object",
                        "x-am-database": "database",
                        "properties": {
                            "id": {"type": "integer", "x-am-primary-key": "auto"},
                            "name": {"type": "string"},
                        },
                    }
                }
            },
        }
    )

    assert "testschema" in ModelFactory.schema_objects
    schema_object = ModelFactory.get_schema_object("testschema")
    assert isinstance(schema_object, SchemaObject)
    assert schema_object.entity == "testschema"


#    assert schema_object.get_property("id").is_primary_key is True


def test_resolve_reference():
    ModelFactory.set_spec(
        {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "TestSchema": {
                        "type": "object",
                        "x-am-database": "database",
                        "properties": {
                            "id": {"type": "integer", "x-am-primary-key": "auto"},
                            "name": {"type": "string"},
                        },
                    }
                }
            },
        }
    )

    openapi_element = OpenAPIElement(
        {
            "title": "TestElement",
            "description": "A test element",
            "required": ["id"],
            "type": "object",
        }
    )

    resolved = openapi_element.resolve_reference("#/components/schemas/TestSchema")
    log.info(f"resolved: {resolved}")
    assert resolved.get("type") == "object"


def test_schema_object_initialization():
    ModelFactory.set_spec(
        {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "TestSchema": {
                        "type": "object",
                        "x-am-database": "testdb",
                        "properties": {
                            "id": {"type": "integer", "x-am-primary-key": "auto"},
                            "name": {"type": "string"},
                        },
                    }
                }
            },
        }
    )

    schema_object = ModelFactory.get_schema_object("testschema")
    assert schema_object.entity == "testschema"
    assert schema_object.database == "testdb"


#    assert schema_object.primary_key.name == "id"


def test_schema_object_property_conversion():
    ModelFactory.set_spec(
        {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "TestSchema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "x-am-primary-key": True},
                            "name": {"type": "string"},
                        },
                    }
                }
            },
        }
    )

    properties = {
        "type": "string",
        "x-am-column-name": "name",
        "x-am-column-type": "string",
        "x-am-primary-key": False,
    }
    property_object = SchemaObjectProperty(
        "test_entity", "name", properties
    )
    db_value = property_object.convert_to_db_value("test_value")
    assert db_value == "test_value"
    api_value = property_object.convert_to_api_value("test_value")
    assert api_value == "test_value"

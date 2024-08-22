import pytest
from unittest.mock import patch, MagicMock
from api_foundry.utils.app_exception import ApplicationException
from api_foundry.utils.logger import logger
from api_foundry.utils.model_factory import (
    ModelFactory,
    SchemaObject,
    SchemaObjectProperty,
    OpenAPIElement,
)

log = logger(__name__)


@pytest.mark.unit
def test_set_spec():
    # Mock the file content of api_spec.yaml
    ModelFactory.set_spec(
        {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "TestSchema": {
                        "type": "object",
                        "x-af-database": "database",
                        "properties": {
                            "id": {"type": "integer", "x-af-primary-key": "auto"},
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
    assert schema_object.operation_id == "testschema"


#    assert schema_object.get_property("id").is_primary_key is True


def test_schema_object_initialization():
    ModelFactory.set_spec(
        {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "TestSchema": {
                        "type": "object",
                        "x-af-database": "testdb",
                        "properties": {
                            "id": {"type": "integer", "x-af-primary-key": "auto"},
                            "name": {"type": "string"},
                        },
                    }
                }
            },
        }
    )

    schema_object = ModelFactory.get_schema_object("testschema")
    assert schema_object.operation_id == "testschema"
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
                            "id": {"type": "integer", "x-af-primary-key": "auto"},
                            "name": {"type": "string"},
                        },
                    }
                }
            },
        }
    )

    properties = {
        "type": "string",
        "x-af-column-name": "name",
        "x-af-column-type": "string",
        "x-af-primary-key": False,
    }
    property_object = SchemaObjectProperty(
        "test_entity", "name", properties, spec=ModelFactory.spec
    )
    db_value = property_object.convert_to_db_value("test_value")
    assert db_value == "test_value"
    api_value = property_object.convert_to_api_value("test_value")
    assert api_value == "test_value"

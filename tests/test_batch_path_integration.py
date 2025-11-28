"""Test batch_path parameter integration in APIFoundry."""
import pytest
import yaml
from api_foundry.iac.gateway_spec import APISpecEditor


@pytest.mark.unit
def test_batch_path_generates_endpoint():
    """Test that batch_path parameter generates the /batch endpoint."""

    # Minimal OpenAPI spec
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "components": {
            "schemas": {
                "album": {
                    "type": "object",
                    "x-af-database": "chinook",
                    "properties": {
                        "album_id": {"type": "integer", "x-af-primary-key": "auto"},
                        "title": {"type": "string"},
                    },
                }
            }
        },
    }

    # Create editor with batch_path
    editor = APISpecEditor(open_api_spec=spec, function=None, batch_path="/batch")

    # Generate the spec
    result_yaml = editor.rest_api_spec()
    result = yaml.safe_load(result_yaml)

    # Verify /batch endpoint exists
    assert "paths" in result
    assert "/batch" in result["paths"]
    assert "post" in result["paths"]["/batch"]

    # Verify batch operation details
    batch_op = result["paths"]["/batch"]["post"]
    assert batch_op["summary"] == "Execute batch operations"
    assert "Batch Operations" in batch_op.get("tags", [])

    # Verify batch schemas exist
    assert "components" in result
    assert "schemas" in result["components"]
    assert "BatchRequest" in result["components"]["schemas"]
    assert "BatchOperation" in result["components"]["schemas"]
    assert "BatchResponse" in result["components"]["schemas"]
    assert "OperationError" in result["components"]["schemas"]
    assert "ErrorResponse" in result["components"]["schemas"]

    # Verify BatchRequest schema structure
    batch_req = result["components"]["schemas"]["BatchRequest"]
    assert "operations" in batch_req["properties"]
    assert "options" in batch_req["properties"]
    assert batch_req["required"] == ["operations"]

    # Verify BatchOperation schema structure
    batch_op_schema = result["components"]["schemas"]["BatchOperation"]
    assert "id" in batch_op_schema["properties"]
    assert "entity" in batch_op_schema["properties"]
    assert "action" in batch_op_schema["properties"]
    # id is optional - only required when operation is referenced
    assert set(batch_op_schema["required"]) == {"entity", "action"}


@pytest.mark.unit
def test_without_batch_path_no_endpoint():
    """Test that without batch_path, no /batch endpoint is generated."""

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "components": {
            "schemas": {
                "album": {
                    "type": "object",
                    "x-af-database": "chinook",
                    "properties": {
                        "album_id": {"type": "integer", "x-af-primary-key": "auto"},
                        "title": {"type": "string"},
                    },
                }
            }
        },
    }

    # Create editor WITHOUT batch_path
    editor = APISpecEditor(open_api_spec=spec, function=None, batch_path=None)

    # Generate the spec
    result_yaml = editor.rest_api_spec()
    result = yaml.safe_load(result_yaml)

    # Verify /batch endpoint does NOT exist
    if "paths" in result:
        assert "/batch" not in result.get("paths", {})

    # Verify batch schemas do NOT exist
    if "components" in result and "schemas" in result["components"]:
        schemas = result["components"]["schemas"]
        assert "BatchRequest" not in schemas
        assert "BatchOperation" not in schemas
        assert "BatchResponse" not in schemas


@pytest.mark.unit
def test_custom_batch_path():
    """Test that batch_path accepts custom paths."""

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "components": {"schemas": {}},
    }

    # Create editor with custom batch path
    editor = APISpecEditor(
        open_api_spec=spec, function=None, batch_path="/operations/bulk"
    )

    # Generate the spec
    result_yaml = editor.rest_api_spec()
    result = yaml.safe_load(result_yaml)

    # Verify custom path exists
    assert "paths" in result
    assert "/operations/bulk" in result["paths"]
    assert "post" in result["paths"]["/operations/bulk"]

    # But NOT the default /batch
    assert "/batch" not in result.get("paths", {})

"""Standalone test for batch_path parameter integration."""
import yaml
from api_foundry.iac.gateway_spec import APISpecEditor


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
    print("\n1. Creating APISpecEditor with batch_path='/batch'...")
    editor = APISpecEditor(open_api_spec=spec, function=None, batch_path="/batch")

    # Generate the spec
    print("2. Generating REST API spec...")
    result_yaml = editor.rest_api_spec()
    result = yaml.safe_load(result_yaml)

    # Verify /batch endpoint exists
    print("3. Verifying /batch endpoint exists...")
    assert "paths" in result, "No paths in result"
    assert "/batch" in result["paths"], "/batch path not found"
    assert "post" in result["paths"]["/batch"], "POST method not found on /batch"
    print("   ✓ /batch POST endpoint exists")

    # Verify batch operation details
    print("4. Verifying batch operation details...")
    batch_op = result["paths"]["/batch"]["post"]
    assert batch_op["summary"] == "Execute batch operations"
    assert "Batch Operations" in batch_op.get("tags", [])
    print("   ✓ Batch operation has correct summary and tags")

    # Verify batch schemas exist
    print("5. Verifying batch component schemas...")
    assert "components" in result
    assert "schemas" in result["components"]
    assert "BatchRequest" in result["components"]["schemas"]
    assert "BatchOperation" in result["components"]["schemas"]
    assert "BatchResponse" in result["components"]["schemas"]
    assert "OperationError" in result["components"]["schemas"]
    assert "ErrorResponse" in result["components"]["schemas"]
    print("   ✓ All 5 batch schemas present")

    # Verify BatchRequest schema structure
    print("6. Verifying BatchRequest schema structure...")
    batch_req = result["components"]["schemas"]["BatchRequest"]
    assert "operations" in batch_req["properties"]
    assert "options" in batch_req["properties"]
    assert batch_req["required"] == ["operations"]
    print("   ✓ BatchRequest has operations and options properties")

    # Verify BatchOperation schema structure
    print("7. Verifying BatchOperation schema structure...")
    batch_op_schema = result["components"]["schemas"]["BatchOperation"]
    assert "id" in batch_op_schema["properties"]
    assert "entity" in batch_op_schema["properties"]
    assert "action" in batch_op_schema["properties"]
    # ID is no longer required - only entity and action
    assert set(batch_op_schema["required"]) == {"entity", "action"}
    print("   ✓ BatchOperation has id (optional), entity, action (required)")

    print("\n✅ All tests passed!")
    return True


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
    print("\n1. Creating APISpecEditor WITHOUT batch_path...")
    editor = APISpecEditor(open_api_spec=spec, function=None, batch_path=None)

    # Generate the spec
    print("2. Generating REST API spec...")
    result_yaml = editor.rest_api_spec()
    result = yaml.safe_load(result_yaml)

    # Verify /batch endpoint does NOT exist
    print("3. Verifying /batch endpoint does NOT exist...")
    if "paths" in result:
        assert "/batch" not in result.get("paths", {})
    print("   ✓ No /batch endpoint generated")

    # Verify batch schemas do NOT exist
    print("4. Verifying batch schemas do NOT exist...")
    if "components" in result and "schemas" in result["components"]:
        schemas = result["components"]["schemas"]
        assert "BatchRequest" not in schemas
        assert "BatchOperation" not in schemas
        assert "BatchResponse" not in schemas
    print("   ✓ No batch schemas generated")

    print("\n✅ All tests passed!")
    return True


def test_custom_batch_path():
    """Test that batch_path accepts custom paths."""

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "components": {"schemas": {}},
    }

    # Create editor with custom batch path
    print("\n1. Creating APISpecEditor with custom path='/operations/bulk'...")
    editor = APISpecEditor(
        open_api_spec=spec, function=None, batch_path="/operations/bulk"
    )

    # Generate the spec
    print("2. Generating REST API spec...")
    result_yaml = editor.rest_api_spec()
    result = yaml.safe_load(result_yaml)

    # Verify custom path exists
    print("3. Verifying custom path exists...")
    assert "paths" in result
    assert "/operations/bulk" in result["paths"]
    assert "post" in result["paths"]["/operations/bulk"]
    print("   ✓ Custom path /operations/bulk exists")

    # But NOT the default /batch
    print("4. Verifying default /batch does NOT exist...")
    assert "/batch" not in result.get("paths", {})
    print("   ✓ Default /batch not generated")

    print("\n✅ All tests passed!")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("BATCH_PATH INTEGRATION TESTS")
    print("=" * 70)

    print("\n" + "=" * 70)
    print("TEST 1: batch_path generates endpoint")
    print("=" * 70)
    test_batch_path_generates_endpoint()

    print("\n" + "=" * 70)
    print("TEST 2: without batch_path, no endpoint")
    print("=" * 70)
    test_without_batch_path_no_endpoint()

    print("\n" + "=" * 70)
    print("TEST 3: custom batch_path")
    print("=" * 70)
    test_custom_batch_path()

    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETE!")
    print("=" * 70)

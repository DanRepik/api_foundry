"""Test custom SQL path operations get integrations."""
import pytest
from api_foundry.iac.gateway_spec import APISpecEditor


class MockFunction:
    """Mock function for testing."""

    def __init__(self, name: str = "test-function"):
        self.name = name
        self.invoke_arn = f"arn:aws:lambda:us-east-1:123456789012:function:{name}"


@pytest.mark.unit
def test_custom_sql_operation_generates_integration():
    """Test that custom SQL operations with x-af-database get integrations."""

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/ingest/trigger": {
                "post": {
                    "summary": "Trigger ingestion",
                    "x-af-database": "test_db",
                    "x-af-sql": "INSERT INTO jobs VALUES ($1, $2)",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "bill_ids": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        }
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "202": {
                            "description": "Job created",
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        }
                    },
                }
            }
        },
    }

    mock_fn = MockFunction("test-lambda")
    editor = APISpecEditor(open_api_spec=spec, function=mock_fn, batch_path=None)

    # Generate spec (should process custom SQL operations)
    _ = editor.rest_api_spec()

    # Verify integration was added
    assert len(editor.integrations) == 1
    assert editor.integrations[0]["path"] == "/ingest/trigger"
    assert editor.integrations[0]["method"] == "post"
    assert editor.integrations[0]["function"] == mock_fn


@pytest.mark.unit
def test_custom_sql_with_path_parameters():
    """Test custom SQL operations with path parameters get integrations."""

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/ingest/status/{job_id}": {
                "get": {
                    "summary": "Get job status",
                    "x-af-database": "test_db",
                    "x-af-sql": "SELECT * FROM jobs WHERE id = $job_id",
                    "parameters": [
                        {
                            "name": "job_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Job status",
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        }
                    },
                }
            }
        },
    }

    mock_fn = MockFunction("test-lambda")
    editor = APISpecEditor(open_api_spec=spec, function=mock_fn, batch_path=None)

    # Generate spec
    _ = editor.rest_api_spec()

    # Verify integration was added
    assert len(editor.integrations) == 1
    assert editor.integrations[0]["path"] == "/ingest/status/{job_id}"
    assert editor.integrations[0]["method"] == "get"
    assert editor.integrations[0]["function"] == mock_fn


@pytest.mark.unit
def test_multiple_custom_sql_operations():
    """Test multiple custom SQL operations all get integrations."""

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/ingest/trigger": {
                "post": {
                    "x-af-database": "test_db",
                    "x-af-sql": "INSERT INTO jobs VALUES ($1)",
                    "responses": {"202": {"description": "Created"}},
                }
            },
            "/ingest/status/{job_id}": {
                "get": {
                    "x-af-database": "test_db",
                    "x-af-sql": "SELECT * FROM jobs WHERE id = $job_id",
                    "parameters": [{"name": "job_id", "in": "path", "required": True}],
                    "responses": {"200": {"description": "Status"}},
                }
            },
            "/stats": {
                "get": {
                    "x-af-database": "test_db",
                    "x-af-sql": "SELECT COUNT(*) FROM jobs",
                    "responses": {"200": {"description": "Stats"}},
                }
            },
        },
    }

    mock_fn = MockFunction("test-lambda")
    editor = APISpecEditor(open_api_spec=spec, function=mock_fn, batch_path=None)

    # Generate spec
    _ = editor.rest_api_spec()

    # Verify all integrations were added
    assert len(editor.integrations) == 3

    paths = [i["path"] for i in editor.integrations]
    assert "/ingest/trigger" in paths
    assert "/ingest/status/{job_id}" in paths
    assert "/stats" in paths


@pytest.mark.unit
def test_non_custom_sql_operations_not_integrated():
    """Test that operations without x-af-database don't get integrations."""

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    # No x-af-database - external or non-DB operation
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    mock_fn = MockFunction("test-lambda")
    editor = APISpecEditor(open_api_spec=spec, function=mock_fn, batch_path=None)

    # Generate spec
    _ = editor.rest_api_spec()

    # Verify no integrations added (health check handled elsewhere)
    assert len(editor.integrations) == 0


@pytest.mark.unit
def test_custom_sql_plus_schema_operations():
    """Custom SQL and schema-based CRUD both get integrations."""

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/ingest/trigger": {
                "post": {
                    "x-af-database": "test_db",
                    "x-af-sql": "INSERT INTO jobs VALUES ($1)",
                    "responses": {"202": {"description": "Created"}},
                }
            }
        },
        "components": {
            "schemas": {
                "job": {
                    "type": "object",
                    "x-af-database": "test_db",
                    "properties": {
                        "id": {"type": "string", "x-af-primary-key": "uuid"},
                        "status": {"type": "string"},
                    },
                }
            }
        },
    }

    mock_fn = MockFunction("test-lambda")
    editor = APISpecEditor(open_api_spec=spec, function=mock_fn, batch_path=None)

    # Generate spec
    _ = editor.rest_api_spec()

    # Should have:
    # 1 custom SQL operation + 7 CRUD operations = 8 total
    assert len(editor.integrations) == 8

    paths = [i["path"] for i in editor.integrations]
    assert "/ingest/trigger" in paths  # Custom SQL
    assert "/job" in paths  # Schema CRUD

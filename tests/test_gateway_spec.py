# test_gateway_spec.py

import re
import pytest
from typing import Any
from cloud_foundry import Function, logger

from api_foundry.iac.gateway_spec import APISpecEditor
from tests.test_fixtures import read_spec, write_spec

log = logger(__name__)


class MockFunction(Function):
    def __init__(self, invoke_url: str):
        self._invoke_url = invoke_url

    def invoke_url(self) -> str:
        return self._invoke_url


date_property = {"type": "string", "format": "date"}
date_time_property = {"type": "string", "format": "date-time"}
integer_property = {"type": "integer", "minimum": 5}


class TestGatewaySpec:
    @pytest.mark.parametrize(
        "property, value, valid",
        [
            (
                integer_property,
                "123",
                True,
            ),
            (
                integer_property,
                "1n23",
                False,
            ),
            (
                integer_property,
                "ne::23",
                True,
            ),
            (
                integer_property,
                "between::2,3",
                True,
            ),
            (
                integer_property,
                "in::2,3,5,7",
                True,
            ),
            (
                integer_property,
                "123456",
                True,
            ),
            (
                date_property,
                "1997-12-33",
                False,
            ),
            (
                date_property,
                "1997-12-01",
                True,
            ),
            (
                date_property,
                "1997-13-01",
                False,
            ),
            (
                date_property,
                "lt::2000-01-01",
                True,
            ),
            (
                date_property,
                "lt::2000-01-01,2001-01-01",
                False,
            ),
            (
                date_property,
                "between::2000-01-01,2001-01-01",
                True,
            ),
            (
                date_property,
                "123",
                False,
            ),
        ],
    )
    def test_generate_regex(self, property: dict[str, Any], value: str, valid: bool):
        spec_editor = APISpecEditor(
            open_api_spec={}, function=MockFunction("url"), function_name="test"
        )
        pattern = spec_editor.generate_regex(property)
        log.info(f"pattern: {pattern}")

        if valid:
            assert re.fullmatch(pattern, value), f"Expected {value} to match {pattern}"
        else:
            # Test invalid input
            assert not re.fullmatch(
                pattern, value
            ), f"Expected {value} to not match {pattern}"

    def test_create_operation(self):
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["genre"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_create_operation("/genre", "genre", schema_object)
        result = rest_api_spec.editor.get_spec_part(["paths", "/genre", "post"])

        log.info(f"result: {result}")

        assert result == {
            "summary": "Create a new genre",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "maxLength": 120}
                            },
                            "required": ["name"],
                        }
                    }
                },
            },
            "responses": {
                "201": {
                    "description": "genre created successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/genre"},
                            }
                        }
                    },
                }
            },
        }

    def test_get_many_operation(self):
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["genre"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_get_many_operation("/genre", "genre", schema_object)
        result = rest_api_spec.editor.get_spec_part(["paths", "/genre", "get"])

        log.info(f"result: {result}")

        assert result == {
            "summary": "Retrieve all genre",
            "parameters": [
                {
                    "in": "query",
                    "name": "genre_id",
                    "required": False,
                    "schema": {
                        "type": "integer",
                        "pattern": "^[\\-\\+]?\\d+$|^(?:lt::|le::|eq::|ne::|ge::|gt::)?[\\-\\+]?\\d+$|^between::[\\-\\+]?\\d+,[\\-\\+]?\\d+$|^not-between::[\\-\\+]?\\d+,[\\-\\+]?\\d+,|^in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$|^not-in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$",
                    },
                    "description": "Filter by genre_id",
                },
                {
                    "in": "query",
                    "name": "name",
                    "required": False,
                    "schema": {
                        "type": "string",
                        "pattern": "^[\\w\\s]{min_length,max_length}$|^(?:lt::|le::|eq::|ne::|ge::|gt::)?[\\w\\s]{min_length,max_length}$|^between::[\\w\\s]{min_length,max_length},[\\w\\s]{min_length,max_length}$|^not-between::[\\w\\s]{min_length,max_length},[\\w\\s]{min_length,max_length},|^in::[\\w\\s]{min_length,max_length}(,[\\w\\s]{min_length,max_length})*$|^not-in::[\\w\\s]{min_length,max_length}(,[\\w\\s]{min_length,max_length})*$",
                    },
                    "description": "Filter by name",
                },
            ],
            "responses": {
                "200": {
                    "description": "A list of genre.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/genre"},
                            }
                        }
                    },
                }
            },
        }

    def test_get_by_id_operation(self):
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["genre"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_get_by_id_operation("/genre", "genre", schema_object)
        result = rest_api_spec.editor.get_spec_part(
            ["paths", "/genre/{genre_id}", "get"]
        )

        log.info(f"result: {result}")

        assert result == {
            "summary": "Retrieve genre by genre_id",
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "description": "ID of the genre to get",
                    "required": True,
                    "schema": {
                        "type": {
                            "type": "integer",
                            "x-af-primary-key": "auto",
                            "description": "Unique identifier for the genre.",
                            "example": 1,
                        }
                    },
                }
            ],
            "responses": {
                "200": {
                    "description": "A list of genre.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/genre"},
                            }
                        }
                    },
                }
            },
        }

    def test_update_by_id_operation_with_cc(self):
        # check invalid concurrency control is present
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["genre"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_update_by_id_operation("/genre", "genre", schema_object)
        result = rest_api_spec.editor.get_spec_part(
            ["paths", "/genre/{genre_id}", "put"]
        )
        assert (
            result is None
        ), "update by id path operation is not valid for schema components with currency control properties"

    def test_update_by_id_operation(self):
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["invoice_line"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_update_by_id_operation(
            "/invoice_line", "invoice_line", schema_object
        )
        result = rest_api_spec.editor.get_spec_part(
            ["paths", "/invoice_line/{key_name}", "put"]
        )
        log.info(f"result: {result}")
        assert result == {
            "summary": "Update an existing invoice_line by invoice_line_id",
            "parameters": [
                {
                    "name": "invoice_line_id",
                    "in": "path",
                    "description": "ID of the invoice_line to update",
                    "required": True,
                    "schema": {
                        "type": "integer",
                        "x-af-primary-key": "auto",
                        "description": "Unique identifier for the invoice_line.",
                        "example": 1,
                    },
                }
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "invoice_id": {"type": "integer"},
                                "track_id": {"type": "integer"},
                                "unit_price": {"type": "number"},
                                "quantity": {"type": "integer"},
                            },
                            "required": [],
                        }
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "invoice_line updated successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/invoice_line"},
                            }
                        }
                    },
                }
            },
        }

    def test_update_with_cc_operation(self):
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["genre"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_update_with_cc_operation(
            "/genre", "genre", schema_object
        )
        result = rest_api_spec.editor.get_spec_part(
            ["paths", "/genre/{genre_id}/version/{version}", "put"]
        )
        log.info(f"result: {result}")

        assert result == {
            "summary": "Update an existing genre by ID",
            "parameters": [
                {
                    "name": "genre_id",
                    "in": "path",
                    "description": "ID of the genre to update",
                    "required": True,
                    "schema": {
                        "type": "integer",
                        "x-af-primary-key": "auto",
                        "description": "Unique identifier for the genre.",
                        "example": 1,
                    },
                },
                {
                    "name": "version",
                    "in": "path",
                    "description": "version of the genre to update",
                    "required": True,
                    "schema": {"type": "integer"},
                },
            ],
            "requestBody": {
                "required": False,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "maxLength": 120}
                            },
                            "required": [],
                        }
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "genre updated successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/genre"},
                            }
                        }
                    },
                }
            },
        }

    def test_update_many(self):
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["invoice_line"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_update_many_operation(
            "/invoice_line", "invoice_line", schema_object
        )
        result = rest_api_spec.editor.get_spec_part(["paths", "/invoice_line", "put"])
        log.info(f"result: {result}")
        assert result == {
            "summary": "Update an existing invoice_line by ID",
            "parameters": [
                {
                    "in": "query",
                    "name": "invoice_line_id",
                    "required": False,
                    "schema": {
                        "type": "integer",
                        "pattern": "^[\\-\\+]?\\d+$|^(?:lt::|le::|eq::|ne::|ge::|gt::)?[\\-\\+]?\\d+$|^between::[\\-\\+]?\\d+,[\\-\\+]?\\d+$|^not-between::[\\-\\+]?\\d+,[\\-\\+]?\\d+,|^in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$|^not-in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$",
                    },
                    "description": "Filter by invoice_line_id",
                },
                {
                    "in": "query",
                    "name": "invoice_id",
                    "required": False,
                    "schema": {
                        "type": "integer",
                        "pattern": "^[\\-\\+]?\\d+$|^(?:lt::|le::|eq::|ne::|ge::|gt::)?[\\-\\+]?\\d+$|^between::[\\-\\+]?\\d+,[\\-\\+]?\\d+$|^not-between::[\\-\\+]?\\d+,[\\-\\+]?\\d+,|^in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$|^not-in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$",
                    },
                    "description": "Filter by invoice_id",
                },
                {
                    "in": "query",
                    "name": "track_id",
                    "required": False,
                    "schema": {
                        "type": "integer",
                        "pattern": "^[\\-\\+]?\\d+$|^(?:lt::|le::|eq::|ne::|ge::|gt::)?[\\-\\+]?\\d+$|^between::[\\-\\+]?\\d+,[\\-\\+]?\\d+$|^not-between::[\\-\\+]?\\d+,[\\-\\+]?\\d+,|^in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$|^not-in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$",
                    },
                    "description": "Filter by track_id",
                },
                {
                    "in": "query",
                    "name": "unit_price",
                    "required": False,
                    "schema": {
                        "type": "number",
                        "pattern": "^[+-]?\\d+(\\.\\d+)?$|^(?:lt::|le::|eq::|ne::|ge::|gt::)?[+-]?\\d+(\\.\\d+)?$|^between::[+-]?\\d+(\\.\\d+)?,[+-]?\\d+(\\.\\d+)?$|^not-between::[+-]?\\d+(\\.\\d+)?,[+-]?\\d+(\\.\\d+)?,|^in::[+-]?\\d+(\\.\\d+)?(,[+-]?\\d+(\\.\\d+)?)*$|^not-in::[+-]?\\d+(\\.\\d+)?(,[+-]?\\d+(\\.\\d+)?)*$",
                    },
                    "description": "Filter by unit_price",
                },
                {
                    "in": "query",
                    "name": "quantity",
                    "required": False,
                    "schema": {
                        "type": "integer",
                        "pattern": "^[\\-\\+]?\\d+$|^(?:lt::|le::|eq::|ne::|ge::|gt::)?[\\-\\+]?\\d+$|^between::[\\-\\+]?\\d+,[\\-\\+]?\\d+$|^not-between::[\\-\\+]?\\d+,[\\-\\+]?\\d+,|^in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$|^not-in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$",
                    },
                    "description": "Filter by quantity",
                },
            ],
            "requestBody": {
                "required": False,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "invoice_line_id": {
                                    "type": "integer",
                                    "x-af-primary-key": "auto",
                                    "description": "Unique identifier for the invoice_line.",
                                    "example": 1,
                                },
                                "invoice_id": {"type": "integer"},
                                "invoice": {
                                    "$ref": "#/components/schemas/invoice",
                                    "x-af-parent-property": "invoice_id",
                                    "description": "Invoice associated with the invoice_line.",
                                },
                                "track_id": {"type": "integer"},
                                "track": {
                                    "$ref": "#/components/schemas/track",
                                    "x-af-parent-property": "track_id",
                                    "description": "Track associated with the invoice_line.",
                                },
                                "unit_price": {"type": "number"},
                                "quantity": {"type": "integer"},
                            },
                            "required": [],
                        }
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "invoice_line updated successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/invoice_line"},
                            }
                        }
                    },
                }
            },
        }

    def test_update_many_with_cc(self):
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["invoice"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_update_many_operation(
            "/invoice", "invoice", schema_object
        )
        result = rest_api_spec.editor.get_spec_part(["paths", "/invoice", "put"])
        log.info(f"result: {result}")
        assert result == None

    def test_delete_by_id_operation_with_cc(self):
        # check invalid concurrency control is present
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["genre"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_delete_by_id_operation("/genre", "genre", schema_object)
        result = rest_api_spec.editor.get_spec_part(
            ["paths", "/genre/{genre_id}", "put"]
        )
        assert (
            result is None
        ), "update by id path operation is not valid for schema components with currency control properties"

    def test_delete_by_id_operation(self):
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["invoice_line"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_delete_by_id_operation(
            "/invoice_line", "invoice_line", schema_object
        )
        result = rest_api_spec.editor.get_spec_part(
            ["paths", "/invoice_line/{invoice_line_id}", "delete"]
        )
        log.info(f"result: {result}")
        assert result == {
            "summary": "Delete an existing invoice_line by invoice_line_id",
            "parameters": [
                {
                    "name": "invoice_line_id",
                    "in": "path",
                    "description": "ID of the invoice_line to update",
                    "required": True,
                    "schema": {
                        "type": {
                            "type": "integer",
                            "x-af-primary-key": "auto",
                            "description": "Unique identifier for the invoice_line.",
                            "example": 1,
                        }
                    },
                }
            ],
            "responses": {
                "204": {
                    "description": "invoice_line deleted successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/invoice_line"},
                            }
                        }
                    },
                }
            },
        }

    def test_delete_with_cc_operation(self):
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["genre"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_delete_with_cc_operation(
            "/genre", "genre", schema_object
        )
        result = rest_api_spec.editor.get_spec_part(
            ["paths", "/genre/{genre_id}/version/{version}", "delete"]
        )
        log.info(f"result: {result}")

        assert result == {
            "summary": "Delete an existing genre by ID",
            "parameters": [
                {
                    "name": "genre_id",
                    "in": "path",
                    "description": "ID of the genre to update",
                    "required": True,
                    "schema": {
                        "type": {
                            "type": "integer",
                            "x-af-primary-key": "auto",
                            "description": "Unique identifier for the genre.",
                            "example": 1,
                        }
                    },
                },
                {
                    "name": "version",
                    "in": "path",
                    "description": "version of the genre to update",
                    "required": True,
                    "schema": {"type": "integer"},
                },
            ],
            "responses": {
                "204": {
                    "description": "genre deleted successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/genre"},
                            }
                        }
                    },
                }
            },
        }

    def test_delete_many(self):
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["invoice_line"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_delete_many_operation(
            "/invoice_line", "invoice_line", schema_object
        )
        result = rest_api_spec.editor.get_spec_part(
            ["paths", "/invoice_line", "delete"]
        )
        log.info(f"result: {result}")
        assert result == {
            "summary": "Delete many existing invoice_line using query",
            "parameters": [
                {
                    "in": "query",
                    "name": "invoice_line_id",
                    "required": False,
                    "schema": {
                        "type": "integer",
                        "pattern": "^[\\-\\+]?\\d+$|^(?:lt::|le::|eq::|ne::|ge::|gt::)?[\\-\\+]?\\d+$|^between::[\\-\\+]?\\d+,[\\-\\+]?\\d+$|^not-between::[\\-\\+]?\\d+,[\\-\\+]?\\d+,|^in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$|^not-in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$",
                    },
                    "description": "Filter by invoice_line_id",
                },
                {
                    "in": "query",
                    "name": "invoice_id",
                    "required": False,
                    "schema": {
                        "type": "integer",
                        "pattern": "^[\\-\\+]?\\d+$|^(?:lt::|le::|eq::|ne::|ge::|gt::)?[\\-\\+]?\\d+$|^between::[\\-\\+]?\\d+,[\\-\\+]?\\d+$|^not-between::[\\-\\+]?\\d+,[\\-\\+]?\\d+,|^in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$|^not-in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$",
                    },
                    "description": "Filter by invoice_id",
                },
                {
                    "in": "query",
                    "name": "track_id",
                    "required": False,
                    "schema": {
                        "type": "integer",
                        "pattern": "^[\\-\\+]?\\d+$|^(?:lt::|le::|eq::|ne::|ge::|gt::)?[\\-\\+]?\\d+$|^between::[\\-\\+]?\\d+,[\\-\\+]?\\d+$|^not-between::[\\-\\+]?\\d+,[\\-\\+]?\\d+,|^in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$|^not-in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$",
                    },
                    "description": "Filter by track_id",
                },
                {
                    "in": "query",
                    "name": "unit_price",
                    "required": False,
                    "schema": {
                        "type": "number",
                        "pattern": "^[+-]?\\d+(\\.\\d+)?$|^(?:lt::|le::|eq::|ne::|ge::|gt::)?[+-]?\\d+(\\.\\d+)?$|^between::[+-]?\\d+(\\.\\d+)?,[+-]?\\d+(\\.\\d+)?$|^not-between::[+-]?\\d+(\\.\\d+)?,[+-]?\\d+(\\.\\d+)?,|^in::[+-]?\\d+(\\.\\d+)?(,[+-]?\\d+(\\.\\d+)?)*$|^not-in::[+-]?\\d+(\\.\\d+)?(,[+-]?\\d+(\\.\\d+)?)*$",
                    },
                    "description": "Filter by unit_price",
                },
                {
                    "in": "query",
                    "name": "quantity",
                    "required": False,
                    "schema": {
                        "type": "integer",
                        "pattern": "^[\\-\\+]?\\d+$|^(?:lt::|le::|eq::|ne::|ge::|gt::)?[\\-\\+]?\\d+$|^between::[\\-\\+]?\\d+,[\\-\\+]?\\d+$|^not-between::[\\-\\+]?\\d+,[\\-\\+]?\\d+,|^in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$|^not-in::[\\-\\+]?\\d+(,[\\-\\+]?\\d+)*$",
                    },
                    "description": "Filter by quantity",
                },
            ],
            "responses": {
                "204": {
                    "description": "invoice_line deleted successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/invoice_line"},
                            }
                        }
                    },
                }
            },
        }

    def test_delete_many_with_cc(self):
        spec = read_spec("./resources/chinook_api.yaml")
        schema_object = spec.get("components", {}).get("schemas", {})["invoice"]
        log.info(f"schema_object: {schema_object}")
        rest_api_spec = APISpecEditor(
            open_api_spec=spec,
            function_name="test_function",
            function=MockFunction("function_url_value"),
        )
        rest_api_spec.generate_delete_many_operation(
            "/invoice", "invoice", schema_object
        )
        result = rest_api_spec.editor.get_spec_part(["paths", "/invoice", "delete"])
        log.info(f"result: {result}")
        assert result is None

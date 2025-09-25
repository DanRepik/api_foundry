# gatway_spec.py

import copy
from typing import Any, Optional

from cloud_foundry import Function
from cloud_foundry.utils.aws_openapi_editor import AWSOpenAPISpecEditor

from cloud_foundry import logger


log = logger(__name__)


class APISpecEditor:
    api_spec: dict
    function: Optional[Function]
    integrations: list[dict]

    def __init__(self, *, open_api_spec: Optional[dict], function: Optional[Function]):
        self.function = function
        self.integrations = []
        self.editor = AWSOpenAPISpecEditor(
            copy.deepcopy(open_api_spec) if open_api_spec else None
        )

    def rest_api_spec(self) -> str:
        schemas = self.editor.get_spec_part(["components", "schemas"], create=False)
        if schemas:
            if isinstance(schemas, dict):
                for schema_name, schema_object in schemas.items():
                    self.generate_crud_operations(schema_name, schema_object)
            elif isinstance(schemas, list):
                for schema_object in schemas:
                    schema_name = schema_object.get("name", None)
                    if schema_name:
                        self.generate_crud_operations(schema_name, schema_object)

        #        self.editor.remove_attributes_with_pattern("^x-af-.*$")

        self.editor.correct_schema_names()
        return self.editor.yaml

    def add_operation(
        self,
        path: str,
        method: str,
        operation: dict,
        schema_name: str,
        schema_object: dict,
        function: Optional[Function] = None,
    ):
        self.integrations.append(
            {"path": path, "method": method, "function": function or self.function}
        )
        self.editor.add_operation(
            path=path,
            method=method,
            operation=operation,
            schema_name=schema_name,
            schema_object=schema_object,
        )

    def generate_regex(self, property: dict[str, Any]) -> str:
        regex_pattern = ""

        if property["type"] == "string" and property.get("format", None) == "date":
            # Assuming ISO 8601 date format (YYYY-MM-DD)
            regex_pattern = r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"  # Date part: YYYY-MM-DD

        elif (
            property["type"] == "string" and property.get("format", None) == "date-time"
        ):
            regex_pattern = (
                r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"  # Date part: YYYY-MM-DD
                r"T"  # Separator: T
                r"([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])"  # Time part: HH:MM:SS
                r"(?:\.\d+)?(?:Z|[+-](?:0[0-9]|1[0-4]):[0-5][0-9])?"  # Optional: fractional seconds and timezone
            )

        elif property["type"] == "string":
            if "pattern" in property:
                regex_pattern = f"{property.get('pattern')}" + regex_pattern
            else:
                max_length = property.get("max_length", 200)
                min_length = property.get("min_length", 0)
                regex_pattern = rf"[\w\s]{min_length},{max_length}"  # Allows letters, numbers, and underscores

        elif property["type"] == "integer":
            signed = property.get("signed", True)
            regex_pattern = r"[\-\+]?\d+" if signed else r"\d+"

        elif property["type"] == "number":
            regex_pattern = r"[+-]?\d+(\.\d+)?"

        if len(regex_pattern) == 0:
            regex_pattern = ".*"

        return (
            rf"^{regex_pattern}$"
            + rf"|^(?:lt::|le::|eq::|ne::|ge::|gt::)?{regex_pattern}$"
            + rf"|^between::{regex_pattern},{regex_pattern}$"
            + rf"|^not-between::{regex_pattern},{regex_pattern},"
            + rf"|^in::{regex_pattern}(,{regex_pattern})*$"
            + rf"|^not-in::{regex_pattern}(,{regex_pattern})*$"
        )

    def generate_query_parameters(self, schema_object: dict[str, Any]):
        parameters = []
        for (
            property_name,
            property_details,
        ) in self.get_input_properties(schema_object, include_primary_key=True).items():
            parameter = {
                "in": "query",
                "name": property_name,
                "required": False,
                "schema": {
                    "type": property_details["type"],
                    "pattern": self.generate_regex(property_details),
                },  # Assuming default type is string
                "description": f"Filter by {property_name}",
            }
            parameters.append(parameter)
        return parameters

    def __list_of_schema(self, schema_name: str):
        return {
            "application/json": {
                "schema": {
                    "type": "array",
                    "items": {"$ref": f"#/components/schemas/{schema_name}"},
                }
            }
        }

    def get_primary_key(
        self, schema_object: dict[str, Any]
    ) -> Optional[tuple[str, dict[str, Any]]]:
        for name, property in schema_object["properties"].items():
            if "x-af-primary-key" in property:
                return (name, property)
        return None

    def get_concurrency_property(
        self, schema_object: dict[str, Any]
    ) -> Optional[tuple[str, dict[str, Any]]]:
        concurrency_property = schema_object.get("x-af-concurrency-control", None)
        if concurrency_property:
            return (
                concurrency_property,
                schema_object["properties"][concurrency_property],
            )
        return None

    def get_input_properties(
        self, schema_object: dict[str, Any], include_primary_key: bool = False
    ) -> dict[str, Any]:
        # Retrieve primary key and concurrency property if they exist
        primary_key = (
            self.get_primary_key(schema_object) if not include_primary_key else None
        )
        concurrency_property = self.get_concurrency_property(schema_object)

        result = dict()
        for name, prop in schema_object["properties"].items():
            if "$ref" in prop:
                ref_parts = prop["$ref"].lstrip("#/").split("/")
                referenced_schema = self.editor.get_spec_part(ref_parts)
                if isinstance(referenced_schema, dict):
                    prop = {**prop, **referenced_schema}
                    prop.pop("$ref")

            if (
                "x-af-parent-property" not in prop
                and "x-af-child-property" not in prop
                and (
                    include_primary_key
                    or name != (primary_key[0] if primary_key else None)
                )
                and name != (concurrency_property[0] if concurrency_property else None)
            ):
                result[name] = prop
        return result

    def get_required_input_properties(
        self,
        schema_object: dict[str, Any],
        input_properties: dict[str, Any],
    ) -> list[str]:
        # Filter the required properties from input properties
        required_properties = schema_object.get("required", [])
        return [name for name in input_properties if name in required_properties]

    def generate_crud_operations(self, schema_name: str, schema_object: dict):
        path = f"/{schema_name.lower()}"
        self.generate_create_operation(path, schema_name, schema_object)
        self.generate_get_by_id_operation(path, schema_name, schema_object)
        self.generate_get_many_operation(path, schema_name, schema_object)
        self.generate_update_by_id_operation(path, schema_name, schema_object)
        self.generate_update_with_cc_operation(path, schema_name, schema_object)
        self.generate_update_many_operation(path, schema_name, schema_object)
        self.generate_delete_by_id_operation(path, schema_name, schema_object)
        self.generate_delete_with_cc_operation(path, schema_name, schema_object)
        self.generate_delete_many_operation(path, schema_name, schema_object)

    def generate_create_operation(
        self, path: str, schema_name: str, schema_object: dict[str, Any]
    ):
        primary_key = self.get_primary_key(schema_object)
        include_primary_key = primary_key and primary_key[1].get("key_type") == "manual"
        input_properties = self.get_input_properties(
            schema_object, include_primary_key=include_primary_key or False
        )
        self.add_operation(
            path=path,
            method="post",
            operation={
                "summary": f"Create a new {schema_name}",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": input_properties,
                                "required": self.get_required_input_properties(
                                    schema_object, input_properties
                                ),
                            }
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": f"{schema_name} created successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
            schema_name=schema_name,
            schema_object=schema_object,
        )

    def generate_get_many_operation(
        self, path: str, schema_name: str, schema_object: dict[str, Any]
    ):
        self.add_operation(
            path=path,
            method="get",
            operation={
                "summary": f"Retrieve all {schema_name}",
                "parameters": self.generate_query_parameters(schema_object),
                "responses": {
                    "200": {
                        "description": f"A list of {schema_name}.",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
            schema_name=schema_name,
            schema_object=schema_object,
        )

    def generate_get_by_id_operation(
        self, path: str, schema_name: str, schema_object: dict[str, Any]
    ):
        key = self.get_primary_key(schema_object)
        if not key:
            return

        key_name = key[0]
        self.add_operation(
            path=f"{path}/{{{key_name}}}",
            method="get",
            operation={
                "summary": f"Retrieve {schema_name} by {key_name}",
                "parameters": [
                    {
                        "name": key_name,
                        "in": "path",
                        "description": f"ID of the {schema_name} to get",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": f"A list of {schema_name}.",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
            schema_name=schema_name,
            schema_object=schema_object,
        )

    def generate_update_by_id_operation(
        self, path: str, schema_name: str, schema_object: dict[str, Any]
    ):
        concurrency = self.get_concurrency_property(schema_object)
        if concurrency:
            return

        key = self.get_primary_key(schema_object)
        if not key:
            return

        key_name = key[0]
        self.add_operation(
            path=f"{path}/{{{key_name}}}",
            method="put",
            operation={
                "summary": f"Update an existing {schema_name} by {key_name}",
                "parameters": [
                    {
                        "name": key_name,
                        "in": "path",
                        "description": f"ID of the {schema_name} to update",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": self.get_input_properties(schema_object),
                                "required": [],  # No properties are marked as required
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": f"{schema_name} updated successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
            schema_name=schema_name,
            schema_object=schema_object,
        )

    def generate_update_with_cc_operation(
        self, path: str, schema_name: str, schema_object: dict[str, Any]
    ):
        # Update operation
        key = self.get_primary_key(schema_object)
        if not key:
            return

        key_name = key[0]
        cc_tuple = self.get_concurrency_property(schema_object)
        if not cc_tuple:
            return

        cc_property_name = cc_tuple[0]
        self.add_operation(
            path=f"{path}/{{{key_name}}}/{cc_property_name}/{{{cc_property_name}}}",
            method="put",
            operation={
                "summary": f"Update an existing {schema_name} by ID",
                "parameters": [
                    {
                        "name": key_name,
                        "in": "path",
                        "description": f"ID of the {schema_name} to update",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": cc_property_name,
                        "in": "path",
                        "description": (
                            cc_property_name + " of the " + schema_name + " to update"
                        ),
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": self.get_input_properties(schema_object),
                                "required": [],
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": f"{schema_name} updated successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
            schema_name=schema_name,
            schema_object=schema_object,
        )

    def generate_update_many_operation(
        self, path: str, schema_name: str, schema_object: dict[str, Any]
    ):
        cc_tuple = self.get_concurrency_property(schema_object)
        if cc_tuple:
            return

        # Update operation
        self.add_operation(
            path=path,
            method="put",
            operation={
                "summary": f"Update an existing {schema_name} by ID",
                "parameters": self.generate_query_parameters(schema_object),
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": schema_object["properties"],
                                "required": [],
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": f"{schema_name} updated successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
            schema_name=schema_name,
            schema_object=schema_object,
        )

        # Delete operation

    def generate_delete_with_cc_operation(
        self, path: str, schema_name: str, schema_object: dict[str, Any]
    ):
        cc_tuple = self.get_concurrency_property(schema_object)
        if not cc_tuple:
            return

        cc_property_name = cc_tuple[0]

        key = self.get_primary_key(schema_object)
        if not key:
            return

        key_name = key[0]

        self.add_operation(
            path=f"{path}/{{{key_name}}}/{cc_property_name}/{{{cc_property_name}}}",
            method="delete",
            operation={
                "summary": f"Delete an existing {schema_name} by ID",
                "parameters": [
                    {
                        "name": key_name,
                        "in": "path",
                        "description": f"ID of the {schema_name} to update",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": cc_property_name,
                        "in": "path",
                        "description": (
                            f"{cc_property_name} of the {schema_name} to update"
                        ),
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                "responses": {
                    "204": {
                        "description": f"{schema_name} deleted successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
            schema_name=schema_name,
            schema_object=schema_object,
        )

    def generate_delete_by_id_operation(
        self, path: str, schema_name: str, schema_object: dict[str, Any]
    ):
        if self.get_concurrency_property(schema_object):
            return

        key = self.get_primary_key(schema_object)
        if not key:
            return

        key_name = key[0]

        self.add_operation(
            path=f"{path}/{{{key_name}}}",
            method="delete",
            operation={
                "summary": f"Delete an existing {schema_name} by {key_name}",
                "parameters": [
                    {
                        "name": key_name,
                        "in": "path",
                        "description": f"ID of the {schema_name} to update",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "204": {
                        "description": f"{schema_name} deleted successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
            schema_name=schema_name,
            schema_object=schema_object,
        )

    def generate_delete_many_operation(
        self, path: str, schema_name: str, schema_object: dict[str, Any]
    ):
        if self.get_concurrency_property(schema_object):
            return

        self.add_operation(
            path=path,
            method="delete",
            operation={
                "summary": f"Delete many existing {schema_name} using query",
                "parameters": self.generate_query_parameters(schema_object),
                "responses": {
                    "204": {
                        "description": f"{schema_name} deleted successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
            schema_name=schema_name,
            schema_object=schema_object,
        )

    def transform_schemas(self, spec_dict):
        for component_name, component_data in (
            spec_dict.get("components", {}).get("schemas", {}).items()
        ):
            # Remove attributes that start with 'x-af'
            attributes_to_remove = [
                key for key in component_data if key.startswith("x-af")
            ]
            for attribute in attributes_to_remove:
                component_data.pop(attribute)

        return spec_dict

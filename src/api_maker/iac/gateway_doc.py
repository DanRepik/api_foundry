import copy
import re

from api_maker.utils.model_factory import (
    ModelFactory,
    SchemaObject,
    SchemaObjectProperty,
)
from api_maker.utils.logger import logger


log = logger(__name__)


class GatewapDocument:
    def __init__(
        self, *, authentication_invoke_arn: str, enable_cors: bool = False
    ):
        document = ModelFactory.document

        self.api_doc = dict(
            self.remove_custom_attributes(copy.deepcopy(document))
        )
        if authentication_invoke_arn:
            self.add_custom_authentication(authentication_invoke_arn)
        if enable_cors:
            self.enable_cors()

        for schema_name in ModelFactory.get_schema_names():
            self.generate_crud_operations(
                schema_name, ModelFactory.get_schema_object(schema_name)
            )

    def remove_custom_attributes(self, obj):
        return self.remove_attributes(obj, "^x-am-.*$")

    def remove_attributes(self, obj, pattern) -> dict | list:
        """
        Remove attributes from an object that match a regular expression pattern.

        Args:
            obj: The object from which attributes will be removed.
            pattern: The regular expression pattern to match attributes.

        Returns:
            obj
        """
        if isinstance(obj, dict):
            return {
                key: self.remove_attributes(value, pattern)
                for key, value in obj.items()
                if not re.match(pattern, key)
            }
        elif isinstance(obj, list):
            return [self.remove_attributes(item, pattern) for item in obj]
        else:
            return obj

    def add_custom_authentication(self, authentication_invoke_arn: str):
        components = self.api_doc.get("components", None)
        if components:
            components["securitySchemes"] = {
                "auth0": {
                    "type": "apiKey",
                    "name": "Authorization",
                    "in": "header",
                    "x-amazon-apigateway-authtype": "custom",
                    "x-amazon-apigateway-authorizer": {
                        "type": "token",
                        "authorizerUri": authentication_invoke_arn,
                        "identityValidationExpression": "^Bearer [-0-9a-zA-Z._]*$",
                        "identitySource": "method.request.header.Authorization",
                        "authorizerResultTtlInSeconds": 60,
                    },
                }
            }

    def add_operation(self, path: str, method: str, operation: dict):
        paths = self.api_doc.setdefault("paths", {})
        paths.setdefault(path, {})[method] = operation

    def enable_cors(self):
        self.add_operation(
            "/{proxy+}",
            "options",
            {
                "consumes": ["application/json"],
                "produces": ["application/json"],
                "responses": {
                    "200": {
                        "description": f"200 response",
                        "schema": {
                            "type": "object",
                        },
                        "headers": {
                            "Access-Control-Allow-Origin": {
                                "type": "string",
                            },
                            "Access-Control-Allow-Methods": {
                                "type": "string",
                            },
                            "Access-Control-Allow-Headers": {
                                "type": "string",
                            },
                        },
                    },
                },
                "x-amazon-apigateway-integration": {
                    "responses": {
                        "default": {
                            "statusCode": 200,
                            "responseParameters": {
                                "method.response.header.Access-Control-Allow-Methods": "'DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT'",
                                "method.response.header.Access-Control-Allow-Headers": "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'",
                                "method.response.header.Access-Control-Allow-Origin": "'*'",
                            },
                            "responseTemplates": {
                                "application/json": "",
                            },
                        },
                    },
                    "requestTemplates": {
                        "application/json": f'{{"statusCode": 200}}',
                    },
                    "passthroughBehavior": "when_no_match",
                    "type": "mock",
                },
            },
        )

        self.api_doc["x-amazon-apigateway-cors"] = {
            "allowOrigins": ["*"],
            "allowCredentials": True,
            "allowMethods": [
                "GET",
                "POST",
                "OPTIONS",
                "PUT",
                "PATCH",
                "DELETE",
            ],
            "allowHeaders": [
                "Origin",
                "X-Requested-With",
                "Content-Type",
                "Accept",
                "Authorization",
            ],
        }

    def generate_regex(self, property: SchemaObjectProperty):
        regex_pattern = ""

        if property.api_type == "string":
            if property.max_length is not None:
                regex_pattern += f"{{0,{property.max_length}}}"

            if property.min_length is not None:
                regex_pattern += f"{{{property.min_length},}}"

            if property.pattern is not None:
                regex_pattern += f"({property.pattern})"

        if property.api_type == "date":
            # Assuming ISO 8601 date format (YYYY-MM-DD)
            regex_pattern = r"\d{4}-\d{2}-\d{2}"

        elif property.api_type == "date-time":
            regex_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"

        elif property.api_type == "integer":
            regex_pattern = r"\d+"

        elif property.api_type == "number":
            regex_pattern = r"\d+(\.\d+)"

        if len(regex_pattern) == 0:
            regex_pattern = ".*"

        return f"^(({regex_pattern})|lt::|le::|eq::|ne::|ge::|gt::|between::({regex_pattern}),|not-between::({regex_pattern}),|in::(({regex_pattern}),)*)$"

    def generate_query_parameters(self, schema_object: SchemaObject):
        parameters = []
        for (
            property_name,
            property_details,
        ) in schema_object.properties.items():
            parameter = {
                "in": "query",
                "name": property_name,
                "required": False,
                "schema": {
                    "type": property_details.type,
                    "pattern": self.generate_regex(property_details),
                },  # Assuming default type is string
                "description": f"Filter by {property_name}",
            }
            parameters.append(parameter)
        return parameters

    def generate_crud_operations(
        self, schema_name, schema_object: SchemaObject
    ):
        path = f"/{schema_name.lower()}"
        self.generate_create_operation(path, schema_name, schema_object)
        self.generate_get_operation(path, schema_name, schema_object)

    #        if schema_object.concurrency_property:
    #            self.generate_update_with_cc_operation(path, schema_name, schema_object)
    #        else:
    #            self.generate_update_by_id_operation(path, schema_name, schema_object)
    #            self.generate_update_many_operation(path, schema_name, schema_object)
    #        self.generate_delete_operation(path, schema_name, schema_object)

    def generate_create_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        self.add_operation(
            path,
            "post",
            {
                "summary": f"Create a new {schema_name}",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": self.remove_custom_attributes(
                                    schema_object.schema_object["properties"]
                                ),
                                "required": schema_object.required,
                            }
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": f"{schema_name} created successfully"
                    }
                },
            },
        )

    def generate_get_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        self.add_operation(
            path,
            "get",
            {
                "summary": f"Retrieve all {schema_name}",
                "parameters": self.generate_query_parameters(schema_object),
                "responses": {
                    "200": {
                        "description": "A list of schema objects.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "$ref": f"#/components/schemas/{schema_name}"
                                    },
                                }
                            }
                        },
                    }
                },
            },
        )

    def generate_get_by_id_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        self.add_operation(
            f"{path}/{{id}}",
            "get",
            {
                "summary": f"Retrieve all {schema_name}",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "description": f"ID of the {schema_name} to get",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "A list of schema objects.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "$ref": f"#/components/schemas/{schema_name}"
                                    },
                                }
                            }
                        },
                    }
                },
            },
        )

    def generate_update_by_id_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        # Update operation
        self.add_operation(
            f"{path}/{{id}}",
            "put",
            {
                "summary": f"Update an existing {schema_name} by ID",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "description": f"ID of the {schema_name} to update",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": schema_object.properties,
                                "required": [],  # No properties are marked as required
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": f"{schema_name} updated successfully"
                    }
                },
            },
        )

    def generate_update_with_cc_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        # Update operation
        key = schema_object.primary_key
        cc_property = schema_object.concurrency_property
        self.add_operation(
            f"{path}/{{{key.name}}}/{cc_property.name}/{{{cc_property.name}}}",
            "put",
            {
                "summary": f"Update an existing {schema_name} by ID",
                "parameters": [
                    {
                        "name": key.name,
                        "in": "path",
                        "description": f"ID of the {schema_name} to update",
                        "required": True,
                        "schema": {"type": key.api_type},
                    },
                    {
                        "name": cc_property.name,
                        "in": "path",
                        "description": f"{cc_property.name} of the {schema_name} to update",
                        "required": True,
                        "schema": {"type": cc_property.api_type},
                    },
                ],
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": schema_object.properties,
                                "required": [],  # No properties are marked as required
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": f"{schema_name} updated successfully"
                    }
                },
            },
        )

    def generate_update_many_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        # Update operation
        self.add_operation(
            path,
            "put",
            {
                "summary": f"Update an existing {schema_name} by ID",
                "parameters": self.generate_query_parameters(schema_object),
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": schema_object.properties,
                                "required": [],  # No properties are marked as required
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": f"{schema_name} updated successfully"
                    }
                },
            },
        )

        # Delete operation

    def generate_delete_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        self.add_operation(
            f"{path}/{{id}}",
            "delete",
            {
                "summary": f"Delete an existing {schema_name} by ID",
                "parameters": self.generate_query_parameters(schema_object),
                "responses": {
                    "204": {
                        "description": f"{schema_name} deleted successfully"
                    }
                },
            },
        )

    def transform_schemas(self, spec_dict):
        for component_name, component_data in (
            spec_dict.get("components", {}).get("schemas", {}).items()
        ):
            # Remove attributes that start with 'x-am'
            attributes_to_remove = [
                key for key in component_data if key.startswith("x-am")
            ]
            for attribute in attributes_to_remove:
                component_data.pop(attribute)

            # Add new custom attributes
            component_data["x-new-attribute1"] = "value1"
            component_data["x-new-attribute2"] = "value2"

        return spec_dict

#!/usr/bin/env python
import json
from api_foundry.utils.model_factory import ModelFactory

model_factory = ModelFactory(
    {
        "openapi": "3.0.0",
        "components": {
            "schemas": {
                "TestSchema": {
                    "type": "object",
                    "x-af-database": "database",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "x-af-primary-key": "auto",
                        },
                        "name": {"type": "string"},
                    },
                }
            }
        },
    }
)

result = model_factory.get_config_output()
print("ACTUAL OUTPUT:")
print(json.dumps(result, indent=2, sort_keys=True))

expected = {
    "schema_objects": {
        "TestSchema": {
            "api_name": "TestSchema",
            "database": "database",
            "table_name": "TestSchema",
            "properties": {
                "id": {
                    "api_name": "id",
                    "column_name": "id",
                    "api_type": "integer",
                    "column_type": "integer",
                    "required": False,
                    "key_type": "auto",
                },
                "name": {
                    "api_name": "name",
                    "column_name": "name",
                    "api_type": "string",
                    "column_type": "string",
                    "required": False,
                },
            },
            "primary_key": "id",
            "relations": {},
            "permissions": {},
            "inject_properties": {},
        }
    },
    "path_operations": {},
}

print("\n\nEXPECTED OUTPUT:")
print(json.dumps(expected, indent=2, sort_keys=True))

print("\n\nMATCH:", result == expected)

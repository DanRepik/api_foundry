import pytest

from api_foundry.utils.model_factory import SchemaObject, ModelFactory


@pytest.fixture
def invoice_with_version_stamp(load_model):
    return SchemaObject(
        "invoice",
        {
            "type": "object",
            "x-am-engine": "postgres",
            "x-am-database": "chinook",
            "x-am-concurrency-control": "version_stamp",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "x-am-primary-key": "auto",
                },
                "customer_id": {"type": "integer"},
                "customer": {
                    "$ref": "#/components/schemas/customer",
                    "x-am-parent-property": "customer_id",
                },
                "invoice_date": {
                    "type": "string",
                    "format": "date-time",
                },
                "billing_address": {"type": "string", "maxLength": 70},
                "billing_city": {"type": "string", "maxLength": 40},
                "billing_state": {"type": "string", "maxLength": 40},
                "billing_country": {"type": "string", "maxLength": 40},
                "billing_postal_code": {
                    "type": "string",
                    "maxLength": 10,
                },
                "line_items": {
                    "type": "array",
                    "items": {
                        "$ref": "#/components/schemas/invoice_line",
                        "x-am-child-property": "invoice_id",
                    },
                },
                "total": {"type": "number", "format": "float"},
                "version_stamp": {"type": "string", "format": "uuid"},
            },
            "required": [
                "invoice_id",
                "customer_id",
                "invoice_date",
                "total",
            ],
        },
        spec=ModelFactory.spec,
    )


@pytest.fixture
def invoice_no_concurrency() -> SchemaObject:
    return SchemaObject(
        "invoice",
        {
            "type": "object",
            "x-am-engine": "postgres",
            "x-am-database": "chinook",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "x-am-primary-key": "auto",
                },
                "customer_id": {"type": "integer"},
                "customer": {
                    "$ref": "#/components/schemas/customer",
                    "x-am-parent-property": "customer_id",
                },
                "invoice_date": {
                    "type": "string",
                    "format": "date-time",
                },
                "billing_address": {"type": "string", "maxLength": 70},
                "billing_city": {"type": "string", "maxLength": 40},
                "billing_state": {"type": "string", "maxLength": 40},
                "billing_country": {"type": "string", "maxLength": 40},
                "billing_postal_code": {
                    "type": "string",
                    "maxLength": 10,
                },
                "line_items": {
                    "type": "array",
                    "items": {
                        "$ref": "#/components/schemas/invoice_line",
                        "x-am-child-property": "invoice_id",
                    },
                },
                "total": {"type": "number", "format": "float"},
                "last_updated": {"type": "string"},
            },
            "required": [
                "invoice_id",
                "customer_id",
                "invoice_date",
                "total",
            ],
        },
        spec=ModelFactory.spec,
    )

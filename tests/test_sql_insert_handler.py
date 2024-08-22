import pytest

from datetime import datetime

from api_foundry.dao.sql_insert_query_handler import SQLInsertSchemaQueryHandler
from api_foundry.utils.app_exception import ApplicationException
from api_foundry.utils.model_factory import ModelFactory, SchemaObject
from api_foundry.operation import Operation
from api_foundry.utils.logger import logger
from test_fixtures import load_model

log = logger(__name__)


@pytest.mark.unit
class TestInsertSQLHandler:
    def test_insert_uuid(self, load_model):
        sql_handler = SQLInsertSchemaQueryHandler(
            Operation(
                operation_id="invoice",
                action="create",
                store_params={
                    "customer_id": "2",
                    "invoice_date": "2024-03-17",
                    "billing_address": "Theodor-Heuss-Straße 34",
                    "billing_city": "Stuttgart",
                    "billing_country": "Germany",
                    "billing_postal_code": "70174",
                    "total": "1.63",
                },
            ),
            SchemaObject(
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
            ),
            "postgres",
        )

        log.info(f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}")

        assert (
            sql_handler.sql
            == "INSERT INTO invoice ( customer_id, invoice_date, billing_address, billing_city, billing_country, billing_postal_code, total, version_stamp ) VALUES ( %(customer_id)s, %(invoice_date)s, %(billing_address)s, %(billing_city)s, %(billing_country)s, %(billing_postal_code)s, %(total)s, gen_random_uuid()) RETURNING invoice_id, customer_id, invoice_date, billing_address, billing_city, billing_state, billing_country, billing_postal_code, total, version_stamp"
        )

        assert sql_handler.placeholders == {
            "customer_id": 2,
            "invoice_date": datetime(2024, 3, 17, 0, 0),
            "billing_address": "Theodor-Heuss-Straße 34",
            "billing_city": "Stuttgart",
            "billing_country": "Germany",
            "billing_postal_code": "70174",
            "total": 1.63,
        }

    def test_insert_no_cc(self, load_model):
        sql_handler = SQLInsertSchemaQueryHandler(
            Operation(
                operation_id="invoice",
                action="create",
                store_params={
                    "customer_id": "2",
                    "invoice_date": "2024-03-17",
                    "billing_address": "Theodor-Heuss-Straße 34",
                    "billing_city": "Stuttgart",
                    "billing_country": "Germany",
                    "billing_postal_code": "70174",
                    "total": "1.63",
                },
            ),
            SchemaObject(
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
                    },
                    "required": [
                        "invoice_id",
                        "customer_id",
                        "invoice_date",
                        "total",
                    ],
                },
                spec=ModelFactory.spec,
            ),
            "postgres",
        )

        log.info(f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}")

        assert (
            sql_handler.sql
            == "INSERT INTO invoice ( customer_id, invoice_date, billing_address, billing_city, billing_country, billing_postal_code, total ) VALUES ( %(customer_id)s, %(invoice_date)s, %(billing_address)s, %(billing_city)s, %(billing_country)s, %(billing_postal_code)s, %(total)s) RETURNING invoice_id, customer_id, invoice_date, billing_address, billing_city, billing_state, billing_country, billing_postal_code, total"
        )

        assert sql_handler.placeholders == {
            "customer_id": 2,
            "invoice_date": datetime(2024, 3, 17, 0, 0),
            "billing_address": "Theodor-Heuss-Straße 34",
            "billing_city": "Stuttgart",
            "billing_country": "Germany",
            "billing_postal_code": "70174",
            "total": 1.63,
        }

    def test_insert_property_selection(self, load_model):
        sql_handler = SQLInsertSchemaQueryHandler(
            Operation(
                operation_id="invoice",
                action="create",
                store_params={
                    "customer_id": "2",
                    "invoice_date": "2024-03-17",
                    "billing_address": "Theodor-Heuss-Straße 34",
                    "billing_city": "Stuttgart",
                    "billing_country": "Germany",
                    "billing_postal_code": "70174",
                    "total": "1.63",
                },
                metadata_params={"_properties": "customer_id invoice_date"},
            ),
            SchemaObject(
                "invoice",
                {
                    "type": "object",
                    "x-am-engine": "postgres",
                    "x-am-database": "chinook",
                    "x-am-concurrency-control": "last_updated",
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
                        "last_updated": {"type": "string", "format": "uuid"},
                    },
                    "required": [
                        "invoice_id",
                        "customer_id",
                        "invoice_date",
                        "total",
                    ],
                },
                spec=ModelFactory.spec,
            ),
            "postgres",
        )

        log.info(f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}")

        assert (
            sql_handler.sql
            == "INSERT INTO invoice ( customer_id, invoice_date, billing_address, billing_city, billing_country, billing_postal_code, total, last_updated ) VALUES ( %(customer_id)s, %(invoice_date)s, %(billing_address)s, %(billing_city)s, %(billing_country)s, %(billing_postal_code)s, %(total)s, gen_random_uuid()) RETURNING customer_id, invoice_date"
        )

        assert sql_handler.placeholders == {
            "customer_id": 2,
            "invoice_date": datetime(2024, 3, 17, 0, 0),
            "billing_address": "Theodor-Heuss-Straße 34",
            "billing_city": "Stuttgart",
            "billing_country": "Germany",
            "billing_postal_code": "70174",
            "total": 1.63,
        }

    def test_insert_bad_key(self, load_model):
        try:
            sql_handler = SQLInsertSchemaQueryHandler(
                Operation(
                    operation_id="genre",
                    action="create",
                    store_params={"genre_id": 34, "description": "Bad genre"},
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-am-engine": "postgres",
                        "x-am-database": "chinook",
                        "properties": {
                            "genre_id": {
                                "type": "integer",
                                "x-am-primary-key": "auto",
                            },
                            "name": {"type": "string", "maxLength": 120},
                        },
                        "required": ["genre_id"],
                    },
                    spec=ModelFactory.spec,
                ),
                "postgres",
            )
            assert False, "Attempt to set primary key during insert did not fail"
        except ApplicationException as e:
            assert (
                e.message
                == "Primary key values cannot be inserted when key type is auto. schema_object: genre"
            )

    def test_insert_missing_required_key(self, load_model):
        try:
            SQLInsertSchemaQueryHandler(
                Operation(
                    operation_id="genre",
                    action="create",
                    store_params={"description": "Bad genre"},
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-am-engine": "postgres",
                        "x-am-database": "chinook",
                        "properties": {
                            "genre_id": {
                                "type": "integer",
                                "x-am-primary-key": "required",
                            },
                            "name": {"type": "string", "maxLength": 120},
                        },
                        "required": ["genre_id"],
                    },
                    spec=ModelFactory.spec,
                ),
                "postgres",
            )
            assert False, "Attempt to insert without a required key did not fail"
        except ApplicationException as e:
            pass

    def test_insert_auto_key(self, load_model):
        try:
            sql_handler = SQLInsertSchemaQueryHandler(
                Operation(
                    operation_id="genre",
                    action="create",
                    store_params={"genre_id": 34, "name": "Good genre"},
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-am-engine": "postgres",
                        "x-am-database": "chinook",
                        "properties": {
                            "genre_id": {
                                "type": "integer",
                                "x-am-primary-key": "auto",
                            },
                            "name": {"type": "string", "maxLength": 120},
                        },
                        "required": ["genre_id"],
                    },
                    spec=ModelFactory.spec,
                ),
                "postgres",
            )
            assert False, "Attempt to set primary key during insert did not fail"
        except ApplicationException as e:
            pass

    def test_insert_sequence(self, load_model):
        sql_handler = SQLInsertSchemaQueryHandler(
            Operation(
                operation_id="genre",
                action="create",
                store_params={"name": "Good genre"},
            ),
            SchemaObject(
                "genre",
                {
                    "x-am-engine": "postgres",
                    "x-am-database": "chinook",
                    "properties": {
                        "genre_id": {
                            "type": "integer",
                            "x-am-primary-key": "sequence",
                            "x-am-sequence-name": "test-sequence",
                        },
                        "name": {"type": "string", "maxLength": 120},
                    },
                    "required": ["genre_id"],
                },
                spec=ModelFactory.spec,
            ),
            "postgres",
        )
        log.info(f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}")

        assert (
            sql_handler.sql
            == "INSERT INTO genre ( name, genre_id ) VALUES ( %(name)s, nextval('test-sequence')) RETURNING genre_id, name"
        )
        assert sql_handler.placeholders == {"name": "Good genre"}

    def test_insert_timestamp(self, load_model):
        try:
            sql_handler = SQLInsertSchemaQueryHandler(
                Operation(
                    operation_id="genre",
                    action="create",
                    store_params={"name": "New genre"},
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-am-engine": "postgres",
                        "x-am-database": "chinook",
                        "x-am-concurrency-control": "last_updated",
                        "properties": {
                            "genre_id": {
                                "type": "integer",
                                "x-am-primary-key": "auto",
                            },
                            "name": {"type": "string", "maxLength": 120},
                            "last_updated": {
                                "type": "string",
                                "format": "date-time",
                            },
                        },
                        "required": ["genre_id"],
                    },
                    spec=ModelFactory.spec,
                ),
                "postgres",
            )
            log.info(
                f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}"
            )
            assert (
                sql_handler.sql
                == "INSERT INTO genre ( name, last_updated ) VALUES ( %(name)s, CURRENT_TIMESTAMP) RETURNING genre_id, name, last_updated"
            )
            assert sql_handler.placeholders == {"name": "New genre"}
        except ApplicationException as e:
            assert False

    def test_insert_cc_with_param(self, load_model):
        try:
            SQLInsertSchemaQueryHandler(
                Operation(
                    operation_id="genre",
                    action="create",
                    store_params={
                        "name": "New genre",
                        "last_updated": "test uuid",
                    },
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-am-engine": "postgres",
                        "x-am-database": "chinook",
                        "x-am-concurrency-control": "last_updated",
                        "properties": {
                            "genre_id": {
                                "type": "integer",
                                "x-am-primary-key": "auto",
                            },
                            "name": {"type": "string", "maxLength": 120},
                            "last_updated": {
                                "type": "string",
                            },
                        },
                        "required": ["genre_id"],
                    },
                    spec=ModelFactory.spec,
                ),
                "postgres",
            )
            assert False, "Attempt to set primary key during insert did not fail"
        except ApplicationException as e:
            assert (
                e.message
                == "Versioned properties can not be supplied a store parameters. schema_object: genre, property: last_updated"
            )

    def test_insert_serial(self, load_model):
        try:
            sql_handler = SQLInsertSchemaQueryHandler(
                Operation(
                    operation_id="genre",
                    action="create",
                    store_params={"name": "New genre"},
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-am-engine": "postgres",
                        "x-am-database": "chinook",
                        "x-am-concurrency-control": "last_updated",
                        "properties": {
                            "genre_id": {
                                "type": "integer",
                                "x-am-primary-key": "auto",
                            },
                            "name": {"type": "string", "maxLength": 120},
                            "last_updated": {
                                "type": "integer",
                            },
                        },
                        "required": ["genre_id"],
                    },
                    spec=ModelFactory.spec,
                ),
                "postgres",
            )
            log.info(
                f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}"
            )
            assert (
                sql_handler.sql
                == "INSERT INTO genre ( name, last_updated ) VALUES ( %(name)s, 1) RETURNING genre_id, name, last_updated"
            )
            assert sql_handler.placeholders == {"name": "New genre"}
        except ApplicationException as e:
            assert False

    def test_insert_sequence_missing_name(self, load_model):
        try:
            sql_handler = SQLInsertSchemaQueryHandler(
                Operation(
                    operation_id="genre",
                    action="create",
                    store_params={"name": "Good genre"},
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-am-engine": "postgres",
                        "x-am-database": "chinook",
                        "properties": {
                            "genre_id": {
                                "type": "integer",
                                "x-am-primary-key": "sequence",
                            },
                            "name": {"type": "string", "maxLength": 120},
                        },
                        "required": ["genre_id"],
                    },
                    spec=ModelFactory.spec,
                ),
                "postgres",
            )
            assert False, "Primary key of sequence without a name did not fail"
        except ApplicationException as e:
            assert (
                e.message
                == "Sequence-based primary keys must have a sequence name. Schema object: genre, Property: genre_id"
            )

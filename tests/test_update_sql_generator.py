import pytest
import yaml

from datetime import date, datetime, time, timezone

from api_maker.dao.sql_delete_generator import SQLDeleteGenerator
from api_maker.dao.sql_insert_generator import SQLInsertGenerator
from api_maker.dao.sql_select_generator import SQLSelectGenerator
from api_maker.dao.sql_subselect_generator import SQLSubselectGenerator
from api_maker.dao.sql_update_generator import SQLUpdateGenerator
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.model_factory import (
    ModelFactory,
    SchemaObject,
)
from api_maker.operation import Operation
from api_maker.utils.logger import logger

from test_fixtures import load_model

log = logger(__name__)


class TestUpdateSQLGenerator:
    def test_update_uuid(self, load_model):
        sql_generator = SQLUpdateGenerator(
            Operation(
                entity="invoice",
                action="update",
                query_params={
                    "customer_id": "2",
                    "last_updated": "this is a guid",
                },
                store_params={"invoice_date": "2024-03-18", "total": "2.63"},
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
                        "last_updated": {"type": "string"},
                    },
                    "required": [
                        "invoice_id",
                        "customer_id",
                        "invoice_date",
                        "total",
                    ],
                },
            ),
            "postgres",
        )

        log.info(
            f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
        )

        assert (
            sql_generator.sql
            == "UPDATE invoice SET invoice_date = %(invoice_date)s, total = %(total)s, last_updated = gen_random_uuid()  WHERE customer_id = %(customer_id)s AND last_updated = %(last_updated)s RETURNING invoice_id, customer_id, invoice_date, billing_address, billing_city, billing_state, billing_country, billing_postal_code, total, last_updated"
        )
        assert sql_generator.placeholders == {
            "customer_id": 2,
            "last_updated": "this is a guid",
            "invoice_date": datetime(2024, 3, 18, 0, 0),
            "total": 2.63,
        }

    def test_update_timestamp(self, load_model):
        sql_generator = SQLUpdateGenerator(
            Operation(
                entity="invoice",
                action="update",
                query_params={
                    "customer_id": "2",
                    "last_updated": "2024-04-20T16:20:00",
                },
                store_params={"invoice_date": "2024-03-18", "total": "2.63"},
            ),
            ModelFactory.get_schema_object("invoice"),
            "posgres",
        )

        log.info(
            f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
        )

        assert (
            sql_generator.sql
            == "UPDATE invoice SET invoice_date = %(invoice_date)s, total = %(total)s, last_updated = CURRENT_TIMESTAMP  WHERE customer_id = %(customer_id)s AND last_updated = %(last_updated)s RETURNING invoice_id, customer_id, invoice_date, billing_address, billing_city, billing_state, billing_country, billing_postal_code, total, last_updated"
        )
        assert sql_generator.placeholders == {
            "customer_id": 2,
            "last_updated": datetime(2024, 4, 20, 16, 20, 0),
            "invoice_date": datetime(2024, 3, 18, 0, 0),
            "total": 2.63,
        }

    def test_update_missing_version(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice",
            action="update",
            query_params={
                "customer_id": "2",
            },
            store_params={"invoice_date": "2024-03-18", "total": "2.63"},
        )
        sql_generator = None
        try:
            sql_generator = SQLUpdateGenerator(operation, schema_object, "postgres")
            log.info(
                f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
            )
            assert False, "Missing exception"
        except ApplicationException as err:
            pass

    def test_update_overwrite_version(self):
        try:
            sql_generator = SQLUpdateGenerator(
                Operation(
                    entity="invoice",
                    action="update",
                    query_params={
                        "customer_id": "2",
                    },
                    store_params={
                        "invoice_date": "2024-03-18",
                        "total": "2.63",
                        "last_updated": "this is not allowed",
                    },
                    metadata_params={"_properties": "invoice_id last_updated"},
                ),
                ModelFactory.get_schema_object("invoice"),
                "postgres",
            )
            log.info(
                f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
            )
            assert False, "Missing exception"
        except ApplicationException as err:
            pass

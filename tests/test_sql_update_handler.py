import pytest

from datetime import datetime

from api_foundry.dao.sql_update_query_handler import SQLUpdateSchemaQueryHandler
from api_foundry.utils.app_exception import ApplicationException
from api_foundry.utils.model_factory import ModelFactory
from api_foundry.operation import Operation
from api_foundry.utils.logger import logger

from test_fixtures import load_model  # noqa F401
from test_schema_objects_fixtures import invoice_with_version_stamp  # noqa F401
from test_schema_objects_fixtures import invoice_no_concurrency  # noqa F401

log = logger(__name__)


@pytest.mark.unit
class TestUpdateSQLHandler:
    def test_update_uuid(self, invoice_with_version_stamp):  # noqa E811
        sql_handler = SQLUpdateSchemaQueryHandler(
            Operation(
                operation_id="invoice",
                action="update",
                query_params={
                    "customer_id": "2",
                    "version_stamp": "this is a guid",
                },
                store_params={"invoice_date": "2024-03-18", "total": "2.63"},
            ),
            invoice_with_version_stamp,
            "postgres",
        )

        log.info(f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}")

        assert (
            sql_handler.sql
            == "UPDATE invoice SET invoice_date = %(invoice_date)s, total = %(total)s, version_stamp = gen_random_uuid()  WHERE customer_id = %(customer_id)s AND version_stamp = %(version_stamp)s RETURNING invoice_id, customer_id, invoice_date, billing_address, billing_city, billing_state, billing_country, billing_postal_code, total, version_stamp"  # noqa E501
        )
        assert sql_handler.placeholders == {
            "customer_id": 2,
            "version_stamp": "this is a guid",
            "invoice_date": datetime(2024, 3, 18, 0, 0),
            "total": 2.63,
        }

    def test_update_bulk_on_concurrency(self, load_model):  # noqa E811
        try:
            SQLUpdateSchemaQueryHandler(
                Operation(
                    operation_id="invoice",
                    action="update",
                    query_params={
                        "customer_id": "in::2,3,4",
                        "last_updated": "2024-01-01T12:00:00",
                    },
                    store_params={"invoice_date": "2024-03-18", "total": "2.63"},
                ),
                ModelFactory.get_schema_object("invoice"),
                "postgres",
            ).sql
            assert False, "Missing exception"
        except ApplicationException as ae:
            assert ae.status_code == 400
            assert (
                ae.message
                == "Concurrency settings prohibit multi-record updates invoice, property: customer_id"  # noqa E501
            )

    def test_update_bulk(self, load_model, invoice_no_concurrency):  # noqa E811
        sql_handler = SQLUpdateSchemaQueryHandler(
            Operation(
                operation_id="invoice",
                action="update",
                query_params={"customer_id": "in::3,4,5"},
                store_params={"invoice_date": "2024-03-18", "total": "2.63"},
            ),
            invoice_no_concurrency,
            "postgres",
        )

        log.info(f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}")

        assert (
            sql_handler.sql
            == "UPDATE invoice SET invoice_date = %(invoice_date)s, total = %(total)s WHERE customer_id IN (%(customer_id_0)s, %(customer_id_1)s, %(customer_id_2)s) RETURNING invoice_id, customer_id, invoice_date, billing_address, billing_city, billing_state, billing_country, billing_postal_code, total, last_updated"  # noqa E501
        )
        assert sql_handler.placeholders == {
            "customer_id_0": 3,
            "customer_id_1": 4,
            "customer_id_2": 5,
            "invoice_date": datetime(2024, 3, 18, 0, 0),
            "total": 2.63,
        }

    def test_update_timestamp(self, load_model):  # noqa E811
        sql_handler = SQLUpdateSchemaQueryHandler(
            Operation(
                operation_id="invoice",
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

        log.info(f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}")

        assert (
            sql_handler.sql
            == "UPDATE invoice SET invoice_date = %(invoice_date)s, total = %(total)s, last_updated = CURRENT_TIMESTAMP  WHERE customer_id = %(customer_id)s AND last_updated = %(last_updated)s RETURNING invoice_id, customer_id, invoice_date, billing_address, billing_city, billing_state, billing_country, billing_postal_code, total, last_updated"  # noqa E501
        )
        assert sql_handler.placeholders == {
            "customer_id": 2,
            "last_updated": datetime(2024, 4, 20, 16, 20, 0),
            "invoice_date": datetime(2024, 3, 18, 0, 0),
            "total": 2.63,
        }

    def test_update_missing_version(self, load_model):  # noqa F811
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            operation_id="invoice",
            action="update",
            query_params={
                "customer_id": "2",
            },
            store_params={"invoice_date": "2024-03-18", "total": "2.63"},
        )
        sql_handler = None
        try:
            sql_handler = SQLUpdateSchemaQueryHandler(
                operation, schema_object, "postgres"
            )
            log.info(
                f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}"
            )
            assert False, "Missing exception"
        except ApplicationException as err:
            assert err.status_code == 400
            assert (
                err.message
                == "Missing required concurrency management property.  schema_object: invoice, property: last_updated"
            )

    def test_update_overwrite_version(self, load_model):  # noqa F811
        try:
            sql_handler = SQLUpdateSchemaQueryHandler(
                Operation(
                    operation_id="invoice",
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
                f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}"
            )
            assert False, "Missing exception"
        except ApplicationException as err:
            assert err.status_code == 400
            assert (
                err.message
                == "Missing required concurrency management property.  schema_object: invoice, property: last_updated"
            )

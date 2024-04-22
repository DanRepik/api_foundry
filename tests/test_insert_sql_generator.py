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
    SchemaObjectProperty,
)
from api_maker.operation import Operation
from api_maker.utils.logger import logger

log = logger(__name__)


class TestInsertSQLGenerator:

    def test_insert(self):

        sql_generator = SQLInsertGenerator(
            Operation(
                entity="invoice",
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
                        "invoice_id": {"type": "integer", "x-am-primary-key": "auto"},
                        "customer_id": {"type": "integer"},
                        "customer": {
                            "x-am-schema-object": "customer",
                            "x-am-parent-property": "customer_id",
                        },
                        "invoice_date": {"type": "string", "format": "date-time"},
                        "billing_address": {"type": "string", "maxLength": 70},
                        "billing_city": {"type": "string", "maxLength": 40},
                        "billing_state": {"type": "string", "maxLength": 40},
                        "billing_country": {"type": "string", "maxLength": 40},
                        "billing_postal_code": {"type": "string", "maxLength": 10},
                        "line_items": {
                            "x-am-schema-object": "invoice_line",
                            "x-am-cardinality": "1:m",
                            "x-am-child-property": "invoice_id",
                        },
                        "total": {"type": "number", "format": "float"},
                        "version_stamp": {"type": "string", "x-am-version": "uuid"},
                    },
                    "required": ["invoice_id", "customer_id", "invoice_date", "total"],
                },
            ),
        )

        log.info(
            f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
        )

        assert (
            sql_generator.sql
            == "INSERT INTO chinook.invoice ( customer_id, invoice_date, billing_address, billing_city, billing_country, billing_postal_code, total ) VALUES ( customer_id, invoice_date, billing_address, billing_city, billing_country, billing_postal_code, total) RETURNING invoice_id, customer_id, invoice_date, billing_address, billing_city, billing_state, billing_country, billing_postal_code, total, version_stamp"
        )

        assert sql_generator.placeholders == {
            "customer_id": 2,
            "invoice_date": datetime(2024, 3, 17, 0, 0),
            "billing_address": "Theodor-Heuss-Straße 34",
            "billing_city": "Stuttgart",
            "billing_country": "Germany",
            "billing_postal_code": "70174",
            "total": 1.63,
        }

    def test_insert_property_selection(self):
        sql_generator = SQLInsertGenerator(
            Operation(
                entity="invoice",
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
                    "properties": {
                        "invoice_id": {"type": "integer", "x-am-primary-key": "auto"},
                        "customer_id": {"type": "integer"},
                        "customer": {
                            "x-am-schema-object": "customer",
                            "x-am-parent-property": "customer_id",
                        },
                        "invoice_date": {"type": "string", "format": "date-time"},
                        "billing_address": {"type": "string", "maxLength": 70},
                        "billing_city": {"type": "string", "maxLength": 40},
                        "billing_state": {"type": "string", "maxLength": 40},
                        "billing_country": {"type": "string", "maxLength": 40},
                        "billing_postal_code": {"type": "string", "maxLength": 10},
                        "line_items": {
                            "x-am-schema-object": "invoice_line",
                            "x-am-cardinality": "1:m",
                            "x-am-child-property": "invoice_id",
                        },
                        "total": {"type": "number", "format": "float"},
                        "version_stamp": {"type": "string", "x-am-version": "uuid"},
                    },
                    "required": ["invoice_id", "customer_id", "invoice_date", "total"],
                },
            ),
        )

        log.info(
            f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
        )

        assert (
            sql_generator.sql
            == "INSERT INTO chinook.invoice ( customer_id, invoice_date, billing_address, billing_city, billing_country, billing_postal_code, total ) VALUES ( customer_id, invoice_date, billing_address, billing_city, billing_country, billing_postal_code, total) RETURNING customer_id, invoice_date"
        )

        assert sql_generator.placeholders == {
            "customer_id": 2,
            "invoice_date": datetime(2024, 3, 17, 0, 0),
            "billing_address": "Theodor-Heuss-Straße 34",
            "billing_city": "Stuttgart",
            "billing_country": "Germany",
            "billing_postal_code": "70174",
            "total": 1.63,
        }

    def test_insert_bad_key(self):
        try:
            sql_generator = SQLInsertGenerator(
                Operation(
                    entity="genre",
                    action="create",
                    store_params={"genre_id": 34, "description": "Bad genre"},
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-am-engine": "postgres",
                        "x-am-database": "chinook",
                        "properties": {
                            "genre_id": {"type": "integer", "x-am-primary-key": "auto"},
                            "name": {"type": "string", "maxLength": 120},
                        },
                        "required": ["genre_id"],
                    },
                ),
            )
            assert False, "Attempt to set primary key during insert did not fail"
        except ApplicationException as e:
            pass

    @pytest.mark.quick
    def test_insert_missing_required_key(self):
        try:
            SQLInsertGenerator(
                Operation(
                    entity="genre",
                    action="create",
                    store_params={"description": "Bad genre"},
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-am-engine": "postgres",
                        "x-am-database": "chinook",
                        "properties": {
                            "genre_id": {"type": "integer", "x-am-primary-key": "required"},
                            "name": {"type": "string", "maxLength": 120},
                        },
                        "required": ["genre_id"],
                    },
                ),
            )
            assert False, "Attempt to insert without a required key did not fail"
        except ApplicationException as e:
            pass

    @pytest.mark.quick
    def test_insert_auto_key(self):
        try:
            sql_generator = SQLInsertGenerator(
                Operation(
                    entity="genre",
                    action="create",
                    store_params={"genre_id": 34, "name": "Good genre"},
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-am-engine": "postgres",
                        "x-am-database": "chinook",
                        "properties": {
                            "genre_id": {"type": "integer", "x-am-primary-key": "auto"},
                            "name": {"type": "string", "maxLength": 120},
                        },
                        "required": ["genre_id"],
                    },
                ),
            )
            assert False, "Attempt to set primary key during insert did not fail"
        except ApplicationException as e:
            pass

    @pytest.mark.quick
    def test_insert_sequence(self):
        sql_generator = SQLInsertGenerator(
            Operation(
                entity="genre",
                action="create",
                store_params={"name": "Good genre"},
            ),
            SchemaObject(
                "genre",
                {
                    "x-am-engine": "postgres",
                    "x-am-database": "chinook",
                    "properties": {
                        "genre_id": {"type": "integer", "x-am-primary-key": "sequence", "x-am-squence-name": "test-sequence"},
                        "name": {"type": "string", "maxLength": 120},
                    },
                    "required": ["genre_id"],
                },
            ),
        )
    @pytest.mark.quick
    def test_insert_sequence_missing_name(self):
        try:
            sql_generator = SQLInsertGenerator(
                Operation(
                    entity="genre",
                    action="create",
                    store_params={"name": "Good genre"},
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-am-engine": "postgres",
                        "x-am-database": "chinook",
                        "properties": {
                            "genre_id": {"type": "integer", "x-am-primary-key": "sequence"},
                            "name": {"type": "string", "maxLength": 120},
                        },
                        "required": ["genre_id"],
                    },
                ),
            )
            assert False, "Primary key of sequence without a name did not fail"
        except ApplicationException as e:
            assert e.message == "Sequence-based primary keys must have a sequence name. Schema object: genre, Property: genre_id"


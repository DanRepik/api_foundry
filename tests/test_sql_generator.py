import pytest
import yaml

from datetime import date, datetime, time, timezone

from api_maker.dao.operation_dao import OperationDAO
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


class TestSQLGenerator:

    def test_field_selection(self):
        ModelFactory.load_spec()

        sql_generator = SQLSelectGenerator(
            Operation(entity="invoice", action="read"),
            ModelFactory.get_schema_object("invoice"),
        )

        log.info(f"prefix_map: {sql_generator.prefix_map}")
        result_map = sql_generator.selection_result_map()
        log.info(f"result_map: {len(result_map)}")
        assert len(result_map) == 10
        assert result_map.get("invoice_id") != None

    def test_field_selection_with_association(self):
        ModelFactory.load_spec()
        operation = Operation(
            entity="invoice",
            action="read",
            metadata_params={"_properties": ".* customer:.*"},
        )
        sql_generator = SQLSelectGenerator(
            Operation(
                entity="invoice",
                action="read",
                metadata_params={"_properties": ".* customer:.*"},
            ),
            ModelFactory.get_schema_object("invoice"),
        )

        result_map = sql_generator.selection_result_map()
        log.info(f"result_map: {result_map}")
        assert len(result_map) == 24
        assert result_map.get("i.invoice_id") != None
        assert result_map.get("c.customer_id") != None
        log.info(f"select_list: {sql_generator.select_list}")
        assert "i.invoice_id" in sql_generator.select_list
        assert "c.customer_id" in sql_generator.select_list

    def test_search_condition(self):
        sql_generator = SQLSelectGenerator(
            Operation(
                entity="invoice",
                action="read",
                query_params={"invoice_id": "24", "total": "gt::5"},
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
                        "invoice_date": {"type": "string", "format": "date-time"},
                        "billing_address": {"type": "string", "maxLength": 70},
                        "billing_city": {"type": "string", "maxLength": 40},
                        "billing_state": {"type": "string", "maxLength": 40},
                        "billing_country": {"type": "string", "maxLength": 40},
                        "billing_postal_code": {"type": "string", "maxLength": 10},
                        "total": {"type": "number", "format": "float"},
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
            == "SELECT invoice_id, customer_id, invoice_date, billing_address, billing_city, billing_state, billing_country, billing_postal_code, total FROM invoice WHERE invoice_id = %(invoice_id)s AND total > %(total)s"
        )
        assert sql_generator.placeholders == {"invoice_id": 24, "total": 5.0}

    def test_search_on_m_property(self):
        ModelFactory.load_spec()
        try:
            operation_dao = OperationDAO(
                Operation(
                    entity="invoice",
                    action="read",
                    query_params={"invoice_id": "24", "line_items.track_id": "gt::5"},
                    metadata_params={"_properties": ".* customer:.*"},
                )
            )

            sql_generator = operation_dao.sql_generator
            log.info(f"sql_generator: {sql_generator}")

            log.info(f"sql: {sql_generator.sql}")
            assert False

        except ApplicationException as e:
            assert (
                e.message
                == "Queries using properties in 1:m associationed is not supported. schema object: invoice, property: line_items.track_id"
            )

    def test_search_invalid_property(self):
        ModelFactory.load_spec()
        try:
            operation_dao = OperationDAO(
                Operation(
                    entity="invoice",
                    action="read",
                    query_params={"invoice_id": "24", "track_id": "gt::5"},
                )
            )

            sql_generator = operation_dao.sql_generator
            log.info(f"sql_generator: {sql_generator}")

            log.info(f"sql: {sql_generator.sql}")
            assert False
        except ApplicationException as e:
            assert (
                e.message
                == "Invalid query parameter, property not found. schema object: invoice, property: track_id"
            )

    def test_search_association_property(self):
        ModelFactory.load_spec()
        try:
            operation_dao = OperationDAO(
                Operation(
                    entity="invoice",
                    action="read",
                    query_params={
                        "invoice_id": "gt::24",
                        "customer.customer_id": "gt::5",
                    },
                )
            )

            sql_generator = operation_dao.sql_generator
            log.info(f"sql_generator: {sql_generator}")

            log.info(
                f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
            )
            assert (
                sql_generator.sql
                == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.total, i.last_updated FROM invoice AS i INNER JOIN customer AS c ON i.customer_id = c.customer_id WHERE i.invoice_id > %(i_invoice_id)s AND c.customer_id > %(c_customer_id)s"
            )
            assert sql_generator.placeholders == {
                "i_invoice_id": 24,
                "c_customer_id": 5,
            }
        except ApplicationException as e:
            assert (
                e.message
                == "Invalid query parameter, property not found. schema object: invoice, property: track_id"
            )

    def test_search_value_assignment_type_relations(self):
        ModelFactory.load_spec()
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice",
            action="read",
            query_params={"invoice_id": 24, "line_items.price": "gt::5"},
        )

        sql_generator = SQLSelectGenerator(operation, schema_object)

        property = SchemaObjectProperty(
            engine="postgres",
            entity="invoice",
            name="invoice_id",
            properties={"type": "number", "format": "float"},
        )

        (sql, placeholders) = sql_generator.search_value_assignment(
            property, "1234", "i"
        )
        print(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.invoice_id = %(i_invoice_id)s"
        assert isinstance(placeholders["i_invoice_id"], float)

        # test greater than
        (sql, placeholders) = sql_generator.search_value_assignment(
            property, "gt::1234", "i"
        )
        print(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.invoice_id > %(i_invoice_id)s"
        assert isinstance(placeholders["i_invoice_id"], float)

        # test between
        (sql, placeholders) = sql_generator.search_value_assignment(
            property, "between::1200,1300", "i"
        )
        print(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.invoice_id BETWEEN %(i_invoice_id_1)s AND %(i_invoice_id_2)s"
        assert isinstance(placeholders["i_invoice_id_1"], float)
        assert len(placeholders) == 2
        assert placeholders["i_invoice_id_1"] == 1200.0
        assert placeholders["i_invoice_id_2"] == 1300.0

        # test in
        (sql, placeholders) = sql_generator.search_value_assignment(
            property, "in::1200,1250,1300", "i"
        )
        print(f"sql: {sql}, properties: {placeholders}")
        assert (
            sql
            == "i.invoice_id IN ( %(i_invoice_id_0)s, %(i_invoice_id_1)s, %(i_invoice_id_2)s)"
        )
        assert isinstance(placeholders["i_invoice_id_1"], float)
        assert len(placeholders) == 3
        assert placeholders["i_invoice_id_0"] == 1200.0
        assert placeholders["i_invoice_id_1"] == 1250.0
        assert placeholders["i_invoice_id_2"] == 1300.0

    def test_search_value_assignment_column_rename(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice",
            action="read",
            query_params={"invoice_id": 24, "line_items.price": "gt::5"},
        )

        sql_generator = SQLSelectGenerator(operation, schema_object)

        property = SchemaObjectProperty(
            engine="postgres",
            entity="invoice",
            name="invoice_id",
            properties={
                "x-am-column-name": "x_invoice_id",
                "type": "string",
                "format": "date",
            },
        )

        (sql, placeholders) = sql_generator.search_value_assignment(
            property, "gt::2000-12-12", "i"
        )
        log.info(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.x_invoice_id > %(i_invoice_id)s"
        assert isinstance(placeholders["i_invoice_id"], date)
        assert placeholders["i_invoice_id"] == date(2000, 12, 12)

    def test_search_value_assignment_datetime(self):
        schema_object = SchemaObject(
            "invoice",
            {
                "type": "object",
                "x-am-engine": "postgres",
                "x-am-database": "chinook",
                "properties": {
                    "last_updated": {"type": "string", "format": "date-time"}
                },
                "required": ["invoice_id", "customer_id", "invoice_date", "total"],
            },
        )

        sql_generator = SQLSelectGenerator(
            Operation(
                entity="invoice", action="read", query_params={"last-updated": date}
            ),
            schema_object,
        )

        (sql, placeholders) = sql_generator.search_value_assignment(
            schema_object.get_property("last_updated"), "gt::2000-12-12T12:34:56Z", "i"  # type: ignore
        )
        log.info(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.last_updated > %(i_last_updated)s"
        assert isinstance(placeholders["i_last_updated"], datetime)
        assert placeholders["i_last_updated"] == datetime(
            2000, 12, 12, 12, 34, 56, tzinfo=timezone.utc
        )

    def test_search_value_assignment_date(self):
        schema_object = SchemaObject(
            "invoice",
            {
                "type": "object",
                "x-am-engine": "postgres",
                "x-am-database": "chinook",
                "properties": {"last_updated": {"type": "string", "format": "date"}},
                "required": ["invoice_id", "customer_id", "invoice_date", "total"],
            },
        )

        sql_generator = SQLSelectGenerator(
            Operation(
                entity="invoice", action="read", query_params={"last-updated": date}
            ),
            schema_object,
        )

        (sql, placeholders) = sql_generator.search_value_assignment(
            schema_object.get_property("last_updated"), "gt::2000-12-12", "i"  # type: ignore
        )
        log.info(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.last_updated > %(i_last_updated)s"
        assert isinstance(placeholders["i_last_updated"], date)
        assert placeholders["i_last_updated"] == date(2000, 12, 12)

    @pytest.mark.skip
    def test_search_value_assignment_bool_to_int(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice", action="read", query_params={"is_active": "true"}
        )
        sql_generator = SQLSelectGenerator(operation, schema_object)

        property = SchemaObjectProperty(
            engine="postgres",
            entity="invoice",
            name="is_active",
            properties={"type": "boolean", "x-am-column-type": "integer"},
        )

        (sql, placeholders) = sql_generator.search_value_assignment(
            property, "true", "i"
        )
        log.info(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.is_active = %(i_is_active)s"
        assert isinstance(placeholders["i_last_updated"], date)
        assert placeholders["i_last_updated"] == date(2000, 12, 12)

    def test_select_invalid_column(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice", action="read", query_params={"not_a_property": "FL"}
        )

        try:
            sql_generator = SQLSelectGenerator(operation, schema_object)
            log.info(f"sql: {sql_generator.sql}")
            assert False
        except ApplicationException as e:
            assert e.status_code == 500

    def test_select_single_joined_table(self):
        ModelFactory.load_spec()
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice",
            action="read",
            query_params={"billing_state": "FL"},
            metadata_params={"_properties": ".* customer:.* line_items:.*"},
        )
        sql_generator = SQLSelectGenerator(operation, schema_object)

        log.info(
            f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
        )

        assert (
            sql_generator.sql
            == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.total, i.last_updated, c.customer_id, c.first_name, c.last_name, c.company, c.address, c.city, c.state, c.country, c.postal_code, c.phone, c.fax, c.email, c.support_rep_id, c.version_stamp FROM invoice AS i INNER JOIN customer AS c ON i.customer_id = c.customer_id WHERE i.billing_state = %(i_billing_state)s"
        )
        assert sql_generator.placeholders == {"i_billing_state": "FL"}

    def test_select_schema_handling_table(self):
        ModelFactory.load_spec()
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice",
            action="read",
            query_params={"billing_state": "FL"},
            metadata_params={"_properties": ".* customer:.* line_items:.*"},
        )
        sql_generator = SQLSelectGenerator(operation, schema_object)

        log.info(
            f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
        )

        assert (
            sql_generator.sql
            == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.total, i.last_updated, c.customer_id, c.first_name, c.last_name, c.company, c.address, c.city, c.state, c.country, c.postal_code, c.phone, c.fax, c.email, c.support_rep_id, c.version_stamp FROM invoice AS i INNER JOIN customer AS c ON i.customer_id = c.customer_id WHERE i.billing_state = %(i_billing_state)s"
        )
        assert sql_generator.placeholders == {"i_billing_state": "FL"}

    def test_select_simple_table(self):
        try:
            sql_generator = SQLSelectGenerator(
                Operation(entity="genre", action="read", query_params={"name": "Bill"}),
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
            log.info(
                f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
            )

            assert (
                sql_generator.sql
                == "SELECT genre_id, name FROM genre WHERE name = %(name)s"
            )
            assert sql_generator.placeholders == {"name": "Bill"}
        except ApplicationException as e:
            assert False, e.message

    def test_select_condition_with_count(self):
        try:
            sql_generator = SQLSelectGenerator(
                Operation(
                    entity="genre",
                    action="read",
                    query_params={"genre_id": "gt::10"},
                    metadata_params={"_count": True},
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
            log.info(
                f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
            )

            assert (
                sql_generator.sql
                == "SELECT count(*) FROM genre WHERE genre_id > %(genre_id)s"
            )
            assert sql_generator.placeholders == {"genre_id": 10}
        except ApplicationException as e:
            assert False, e.message

    def test_select_single_table_no_conditions(self):
        try:
            sql_generator = SQLSelectGenerator(
                Operation(entity="genre", action="read"),
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
            log.info(
                f"sql-x: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
            )

            assert sql_generator.sql == "SELECT genre_id, name FROM genre"
            assert sql_generator.placeholders == {}

        except ApplicationException as e:
            assert False, e.message

    def test_delete(self):
        ModelFactory.load_spec()
        schema_object = ModelFactory.get_schema_object("playlist_track")
        operation = Operation(
            entity="playlist_track",
            action="delete",
            query_params={
                "playlist_id": "2",
            },
            metadata_params={"_properties": "track_id"},
        )
        sql_generator = SQLDeleteGenerator(operation, schema_object)

        log.info(
            f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
        )

        assert (
            sql_generator.sql
            == "DELETE FROM playlist_track WHERE playlist_id = %(playlist_id)s RETURNING track_id"
        )
        assert sql_generator.placeholders == {"playlist_id": 2}

    def test_relation_search_condition(self):
        ModelFactory.load_spec()

        operation = Operation(
            entity="invoice",
            action="read",
            query_params={"billing_state": "FL"},
            metadata_params={"_properties": ".* customer:.* line_items:.*"},
        )
        schema_object = ModelFactory.get_schema_object("invoice")
        sql_generator = SQLSelectGenerator(operation, schema_object)

        log.info(f"sql_generator: {sql_generator.sql}")
        assert (
            sql_generator.sql
            == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.total, i.last_updated, c.customer_id, c.first_name, c.last_name, c.company, c.address, c.city, c.state, c.country, c.postal_code, c.phone, c.fax, c.email, c.support_rep_id, c.version_stamp FROM invoice AS i INNER JOIN customer AS c ON i.customer_id = c.customer_id WHERE i.billing_state = %(i_billing_state)s"
        )

        subselect_sql_generator = SQLSubselectGenerator(
            operation,
            schema_object.get_relation("line_items"),
            SQLSelectGenerator(operation, schema_object),
        )

        log.info(f"subselect_sql_generator: {subselect_sql_generator.sql}")
        assert (
            subselect_sql_generator.sql
            == "SELECT invoice_id, invoice_line_id, track_id, unit_price, quantity FROM invoice_line WHERE invoice_id IN ( SELECT invoice_id FROM invoice AS i INNER JOIN customer AS c ON i.customer_id = c.customer_id WHERE i.billing_state = %(i_billing_state)s )"
        )

        select_map = subselect_sql_generator.selection_result_map()
        log.info(f"select_map: {select_map}")

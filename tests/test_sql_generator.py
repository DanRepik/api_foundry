import pytest

from datetime import date, datetime, time, timezone

from api_maker.dao.sql_delete_generator import SQLDeleteGenerator
from api_maker.dao.sql_insert_generator import SQLInsertGenerator
from api_maker.dao.sql_select_generator import SQLSelectGenerator
from api_maker.dao.sql_subselect_generator import SQLSubselectGenerator
from api_maker.dao.sql_update_generator import SQLUpdateGenerator
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.model_factory import ModelFactory, SchemaObjectProperty
from api_maker.operation import Operation
from api_maker.utils.logger import logger

log = logger(__name__)


class TestSQLGenerator:

    def test_field_selection(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(entity="invoice", action="read")

        sql_generator = SQLSelectGenerator(operation, schema_object)

        log.info(f"prefix_map: {sql_generator.prefix_map}")
        log.info(f"result_map: {len(sql_generator.selection_result_map)}")
        assert len(sql_generator.selection_result_map) == 9

        operation = Operation(
            entity="invoice",
            action="read",
            metadata_params={"_properties": ".* line_items:.*"},
        )
        sql_generator = SQLSelectGenerator(operation, schema_object)

        log.info(f"result_map: {len(sql_generator.selection_result_map)}")
        assert len(sql_generator.selection_result_map) == 14
        log.info(f"select_list: {sql_generator.select_list}")

    def test_search_condition(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice",
            action="read",
            query_params={"invoice_id": "24", "line_items.unit_price": "gt:5"},
        )

        sql_generator = SQLSelectGenerator(operation, schema_object)
        log.info(f"search_condition: {sql_generator.search_condition}")

    def test_search_value_assignment_type_relations(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice",
            action="read",
            query_params={"invoice_id": 24, "line_items.price": "gt:5"},
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
            property, "gt:1234", "i"
        )
        print(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.invoice_id > %(i_invoice_id)s"
        assert isinstance(placeholders["i_invoice_id"], float)

        # test between
        (sql, placeholders) = sql_generator.search_value_assignment(
            property, "between:1200,1300", "i"
        )
        print(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.invoice_id BETWEEN %(i_invoice_id_1)s AND %(i_invoice_id_2)s"
        assert isinstance(placeholders["i_invoice_id_1"], float)
        assert len(placeholders) == 2
        assert placeholders["i_invoice_id_1"] == 1200.0
        assert placeholders["i_invoice_id_2"] == 1300.0

        # test in
        (sql, placeholders) = sql_generator.search_value_assignment(
            property, "in:1200,1250,1300", "i"
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
            query_params={"invoice_id": 24, "line_items.price": "gt:5"},
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
            property, "gt:2000-12-12", "i"
        )
        log.info(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.x_invoice_id > %(i_invoice_id)s"
        assert isinstance(placeholders["i_invoice_id"], date)
        assert placeholders["i_invoice_id"] == date(2000, 12, 12)

    def test_search_value_assignment_datetime(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice", action="read", query_params={"last-updated": date}
        )

        sql_generator = SQLSelectGenerator(operation, schema_object)

        # test date-time
        property = SchemaObjectProperty(
            engine="postgres",
            entity="invoice",
            name="last_updated",
            properties={"type": "string", "format": "date-time"},
        )

        (sql, placeholders) = sql_generator.search_value_assignment(
            property, "gt:2000-12-12T12:34:56Z", "i"
        )
        log.info(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.last_updated > %(i_last_updated)s"
        assert isinstance(placeholders["i_last_updated"], datetime)
        assert placeholders["i_last_updated"] == datetime(
            2000, 12, 12, 12, 34, 56, tzinfo=timezone.utc
        )

    def test_search_value_assignment_date(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice", action="read", query_params={"last-updated": date}
        )
        sql_generator = SQLSelectGenerator(operation, schema_object)

        property = SchemaObjectProperty(
            engine="postgres",
            entity="invoice",
            name="last_updated",
            properties={"type": "string", "format": "date"},
        )

        (sql, placeholders) = sql_generator.search_value_assignment(
            property, "gt:2000-12-12", "i"
        )
        log.info(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.last_updated > %(i_last_updated)s"
        assert isinstance(placeholders["i_last_updated"], date)
        assert placeholders["i_last_updated"] == date(2000, 12, 12)

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
            == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.last_updated, i.total, c.customer_id, c.first_name, c.last_name, c.company, c.address, c.city, c.state, c.country, c.postal_code, c.phone, c.fax, c.email, c.support_rep_id FROM chinook.invoice AS i INNER JOIN chinook.customer AS c ON i.customer_id = c.customer_id WHERE i.billing_state = %(i_billing_state)s"
        )
        assert sql_generator.placeholders == {"i_billing_state": "FL"}

    def test_select_simple_table(self):
        schema_object = ModelFactory.get_schema_object("media_type")
        operation = Operation(
            entity="media_type", action="read", query_params={"media_type_id": "23"}
        )
        sql_generator = SQLSelectGenerator(operation, schema_object)

        log.info(
            f"sql-x: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
        )

        assert (
            sql_generator.sql
            == "SELECT media_type_id, name FROM chinook.MetaType WHERE media_type_id = %(media_type_id)s"
        )
        assert sql_generator.placeholders == {"media_type_id": 23}

    def test_select_single_table_no_conditions(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(entity="invoice", action="read")
        sql_generator = SQLSelectGenerator(operation, schema_object)

        log.info(
            f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
        )

        assert (
            sql_generator.sql
            == "SELECT invoice_id, customer_id, invoice_date, billing_address, billing_city, billing_state, billing_country, billing_postal_code, last_updated, total FROM chinook.invoice"
        )
        assert sql_generator.placeholders == {}

    def test_insert(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
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
        )
        sql_generator = SQLInsertGenerator(operation, schema_object)

        log.info(
            f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
        )

        assert (
            sql_generator.sql
            == "INSERT INTO chinook.invoice ( customer_id, invoice_date, billing_address, billing_city, billing_country, billing_postal_code, total ) VALUES ( customer_id, invoice_date, billing_address, billing_city, billing_country, billing_postal_code, total) RETURNING invoice_id, customer_id, invoice_date, billing_address, billing_city, billing_state, billing_country, billing_postal_code, last_updated, total"
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

    def test_update(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice",
            action="update",
            query_params={
                "customer_id": "2",
            },
            store_params={"invoice_date": "2024-03-18", "total": "2.63"},
            metadata_params={"_properties": "invoice_id last_updated"},
        )
        sql_generator = SQLUpdateGenerator(operation, schema_object)

        log.info(
            f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
        )

        assert (
            sql_generator.sql
            == "UPDATE chinook.invoice SET invoice_date = %(invoice_date)s, total = %(total)s WHERE customer_id = %(customer_id)s RETURNING invoice_id, last_updated"
        )
        assert sql_generator.placeholders == {
            "customer_id": 2,
            "invoice_date": datetime(2024, 3, 18, 0, 0),
            "total": 2.63,
        }

    def test_delete(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice",
            action="delete",
            query_params={
                "customer_id": "2",
            },
            metadata_params={"_properties": "invoice_id"},
        )
        sql_generator = SQLDeleteGenerator(operation, schema_object)

        log.info(
            f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}"
        )

        assert (
            sql_generator.sql
            == "DELETE FROM chinook.invoice WHERE customer_id = %(customer_id)s RETURNING invoice_id"
        )
        assert sql_generator.placeholders == {"customer_id": 2}

    @pytest.mark.quick
    def test_relation_search_condition(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            entity="invoice",
            action="read",
            query_params={"billing_state": "FL"},
            metadata_params={"_properties": ".* customer:.* line_items:.*"},
        )
        sql_generator = SQLSelectGenerator(operation, schema_object)
        log.info(f"sql_generator: {sql_generator.sql}")
        assert sql_generator.sql == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.last_updated, i.total, c.customer_id, c.first_name, c.last_name, c.company, c.address, c.city, c.state, c.country, c.postal_code, c.phone, c.fax, c.email, c.support_rep_id FROM chinook.invoice AS i INNER JOIN chinook.customer AS c ON i.customer_id = c.customer_id WHERE i.billing_state = %(i.billing_state)s"

        subselect_sql_generator = SQLSubselectGenerator(operation, schema_object.get_relation("line_items"), SQLSelectGenerator(operation, schema_object))

        log.info(f"subselect_sql_generator: {subselect_sql_generator.sql}")
        assert subselect_sql_generator.sql == "SELECT invoice_id, invoice_line_id, track_id, unit_price, quantity FROM chinook.invoice_line WHERE invoice_id IN ( SELECT invoice_id FROM chinook.invoice AS i INNER JOIN chinook.customer AS c ON i.customer_id = c.customer_id WHERE i.billing_state = %(i.billing_state)s )"

        select_map = subselect_sql_generator.selection_result_map()
        log.info(f"select_map: {select_map}")


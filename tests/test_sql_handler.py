import pytest

from datetime import date, datetime, timezone

from api_foundry.dao.operation_dao import OperationDAO
from api_foundry.dao.sql_delete_query_handler import SQLDeleteSchemaQueryHandler
from api_foundry.dao.sql_select_query_handler import SQLSelectSchemaQueryHandler
from api_foundry.dao.sql_subselect_query_handler import SQLSubselectSchemaQueryHandler
from api_foundry.utils.app_exception import ApplicationException
from api_foundry.utils.model_factory import (
    ModelFactory,
    SchemaObject,
    SchemaObjectProperty,
)
from api_foundry.operation import Operation
from api_foundry.utils.logger import logger
from test_fixtures import load_model  # noqa F401


log = logger(__name__)


@pytest.mark.unit
class TestSQLHandler:
    def test_field_selection(self, load_model):  # noqa F811
        sql_handler = SQLSelectSchemaQueryHandler(
            Operation(operation_id="invoice", action="read"),
            ModelFactory.get_schema_object("invoice"),
            "postgres",
        )
        log.info(f"prefix_map: {sql_handler.prefix_map}")
        result_map = sql_handler.selection_result_map()
        log.info(f"result_map: {len(result_map)}")
        assert len(result_map) == 10
        assert result_map.get("i.invoice_id") is not None

    def test_field_selection_with_association(self, load_model):  # noqa F811
        sql_handler = SQLSelectSchemaQueryHandler(
            Operation(
                operation_id="invoice",
                action="read",
                metadata_params={"properties": ".* customer:.*"},
            ),
            ModelFactory.get_schema_object("invoice"),
            "postgres",
        )

        result_map = sql_handler.selection_result_map()
        log.info(f"result_map: {result_map}")
        assert len(result_map) == 24
        assert result_map.get("i.invoice_id") is not None
        assert result_map.get("c.customer_id") is not None
        log.info(f"select_list: {sql_handler.select_list}")
        assert "i.invoice_id" in sql_handler.select_list
        assert "c.customer_id" in sql_handler.select_list

    def test_search_condition(self, load_model):  # noqa F811
        sql_handler = SQLSelectSchemaQueryHandler(
            Operation(
                operation_id="invoice",
                action="read",
                query_params={"invoice_id": "24", "total": "gt::5"},
            ),
            ModelFactory.get_schema_object("invoice"),
            "postgres",
        )

        log.info(f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}")

        assert (
            sql_handler.sql
            == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.total, i.last_updated FROM invoice AS i WHERE i.invoice_id = %(i_invoice_id)s AND i.total > %(i_total)s"  # noqa E501
        )
        assert sql_handler.placeholders == {"i_invoice_id": 24, "i_total": 5.0}

    @pytest.mark.skip
    def test_search_on_m_property(self, load_model):  # noqa F811
        try:
            operation_dao = OperationDAO(
                Operation(
                    operation_id="invoice",
                    action="read",
                    query_params={"invoice_id": "24", "line_items.track_id": "gt::5"},
                    metadata_params={"_properties": ".* customer:.*"},
                ),
                "postgres",
            )

            sql_handler = operation_dao.query_handler
            log.info(f"sql_handler: {sql_handler}")

            log.info(f"sql: {sql_handler.sql}")
            assert False

        except ApplicationException as e:
            assert (
                e.message
                == "Queries using properties in arrays is not supported. schema object: invoice, property: line_items.track_id"  # noqa E501
            )

    def test_search_invalid_property(self, load_model):  # noqa F811
        try:
            operation_dao = OperationDAO(
                Operation(
                    operation_id="invoice",
                    action="read",
                    query_params={"invoice_id": "24", "track_id": "gt::5"},
                ),
                "postgres",
            )

            sql_operation = operation_dao.query_handler
            log.info(f"sql_operation: {sql_operation}")

            log.info(f"sql: {sql_operation.sql}")
            assert False
        except ApplicationException as e:
            assert (
                e.message
                == "Invalid query parameter, property not found. schema object: invoice, property: track_id"  # noqa E501
            )

    def test_search_association_property(self, load_model):  # noqa F811
        try:
            operation_dao = OperationDAO(
                Operation(
                    operation_id="invoice",
                    action="read",
                    query_params={
                        "invoice_id": "gt::24",
                        "customer.customer_id": "gt::5",
                    },
                ),
                "postgres",
            )

            sql_operation = operation_dao.query_handler
            log.info(f"sql_handler: {sql_operation}")

            log.info(
                f"sql: {sql_operation.sql}, placeholders: {sql_operation.placeholders}"
            )
            assert (
                sql_operation.sql
                == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.total, i.last_updated FROM invoice AS i INNER JOIN customer AS c ON i.customer_id = c.customer_id WHERE i.invoice_id > %(i_invoice_id)s AND c.customer_id > %(c_customer_id)s"  # noqa E501
            )
            assert sql_operation.placeholders == {
                "i_invoice_id": 24,
                "c_customer_id": 5,
            }
        except ApplicationException as e:
            assert (
                e.message
                == "Invalid query parameter, property not found. schema object: invoice, property: track_id"  # noqa E501
            )

    def test_search_value_assignment_type_relations(self, load_model):  # noqa F811
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            operation_id="invoice",
            action="read",
            query_params={"invoice_id": 24, "line_items.price": "gt::5"},
        )

        sql_handler = SQLSelectSchemaQueryHandler(operation, schema_object, "postgres")

        property = SchemaObjectProperty(
            operation_id="invoice",
            name="invoice_id",
            properties={"type": "number", "format": "float"},
            spec=ModelFactory.spec,
        )

        (sql, placeholders) = sql_handler.search_value_assignment(property, "1234", "i")
        print(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.invoice_id = %(i_invoice_id)s"
        assert isinstance(placeholders["i_invoice_id"], float)

        # test greater than
        (sql, placeholders) = sql_handler.search_value_assignment(
            property, "gt::1234", "i"
        )
        print(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.invoice_id > %(i_invoice_id)s"
        assert isinstance(placeholders["i_invoice_id"], float)

        # test between
        (sql, placeholders) = sql_handler.search_value_assignment(
            property, "between::1200,1300", "i"
        )
        print(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.invoice_id BETWEEN %(i_invoice_id_1)s AND %(i_invoice_id_2)s"
        assert isinstance(placeholders["i_invoice_id_1"], float)
        assert len(placeholders) == 2
        assert placeholders["i_invoice_id_1"] == 1200.0
        assert placeholders["i_invoice_id_2"] == 1300.0

        # test in
        (sql, placeholders) = sql_handler.search_value_assignment(
            property, "in::1200,1250,1300", "i"
        )
        print(f"sql: {sql}, properties: {placeholders}")
        assert (
            sql
            == "i.invoice_id IN (%(i_invoice_id_0)s, %(i_invoice_id_1)s, %(i_invoice_id_2)s)"  # noqa E501
        )
        assert isinstance(placeholders["i_invoice_id_1"], float)
        assert len(placeholders) == 3
        assert placeholders["i_invoice_id_0"] == 1200.0
        assert placeholders["i_invoice_id_1"] == 1250.0
        assert placeholders["i_invoice_id_2"] == 1300.0

    def test_search_value_assignment_column_rename(self, load_model):  # noqa F811
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            operation_id="invoice",
            action="read",
            query_params={"invoice_id": 24, "line_items.price": "gt::5"},
        )

        sql_handler = SQLSelectSchemaQueryHandler(operation, schema_object, "postgres")

        property = SchemaObjectProperty(
            operation_id="invoice",
            name="invoice_id",
            properties={
                "x-af-column-name": "x_invoice_id",
                "type": "string",
                "format": "date",
            },
            spec=ModelFactory.spec,
        )

        (sql, placeholders) = sql_handler.search_value_assignment(
            property, "gt::2000-12-12", "i"
        )
        log.info(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.x_invoice_id > %(i_invoice_id)s"
        assert isinstance(placeholders["i_invoice_id"], date)
        assert placeholders["i_invoice_id"] == date(2000, 12, 12)

    def test_search_value_assignment_datetime(self, load_model):  # noqa F811
        schema_object = SchemaObject(
            "invoice",
            {
                "type": "object",
                "x-af-engine": "postgres",
                "x-af-database": "chinook",
                "properties": {
                    "last_updated": {"type": "string", "format": "date-time"}
                },
                "required": ["invoice_id", "customer_id", "invoice_date", "total"],
            },
            spec=ModelFactory.spec,
        )

        sql_handler = SQLSelectSchemaQueryHandler(
            Operation(
                operation_id="invoice",
                action="read",
                query_params={"last-updated": date},
            ),
            schema_object,
            "postgres",
        )

        (sql, placeholders) = sql_handler.search_value_assignment(
            schema_object.get_property("last_updated"), "gt::2000-12-12T12:34:56Z", "i"  # type: ignore # noqa E501
        )
        log.info(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.last_updated > %(i_last_updated)s"
        assert isinstance(placeholders["i_last_updated"], datetime)
        assert placeholders["i_last_updated"] == datetime(
            2000, 12, 12, 12, 34, 56, tzinfo=timezone.utc
        )

    def test_search_value_assignment_date(self, load_model):  # noqa F811
        schema_object = SchemaObject(
            "invoice",
            {
                "type": "object",
                "x-af-engine": "postgres",
                "x-af-database": "chinook",
                "properties": {"last_updated": {"type": "string", "format": "date"}},
                "required": ["invoice_id", "customer_id", "invoice_date", "total"],
            },
            spec=ModelFactory.spec,
        )

        sql_handler = SQLSelectSchemaQueryHandler(
            Operation(
                operation_id="invoice",
                action="read",
                query_params={"last-updated": date},
            ),
            schema_object,
            "postgres",
        )

        (sql, placeholders) = sql_handler.search_value_assignment(
            schema_object.get_property("last_updated"), "gt::2000-12-12", "i"  # type: ignore # noqa E501
        )
        log.info(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.last_updated > %(i_last_updated)s"
        assert isinstance(placeholders["i_last_updated"], date)
        assert placeholders["i_last_updated"] == date(2000, 12, 12)

    @pytest.mark.skip
    def test_search_value_assignment_bool_to_int(self, load_model):  # noqa F811
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            operation_id="invoice", action="read", query_params={"is_active": "true"}
        )
        sql_handler = SQLSelectSchemaQueryHandler(operation, schema_object, "postgres")

        property = SchemaObjectProperty(
            operation_id="invoice",
            name="is_active",
            properties={"type": "boolean", "x-af-column-type": "integer"},
            spec=ModelFactory.spec,
        )

        (sql, placeholders) = sql_handler.search_value_assignment(property, "true", "i")
        log.info(f"sql: {sql}, properties: {placeholders}")
        assert sql == "i.is_active = %(i_is_active)s"
        assert isinstance(placeholders["i_last_updated"], date)
        assert placeholders["i_last_updated"] == date(2000, 12, 12)

    def test_select_invalid_column(self):
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            operation_id="invoice", action="read", query_params={"not_a_property": "FL"}
        )

        try:
            sql_handler = SQLSelectSchemaQueryHandler(
                operation, schema_object, "postgres"
            )
            log.info(f"sql: {sql_handler.sql}")
            assert False
        except ApplicationException as e:
            assert e.status_code == 500

    def test_select_single_joined_table(self, load_model):  # noqa F811
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            operation_id="invoice",
            action="read",
            query_params={"billing_state": "FL"},
            metadata_params={"properties": ".* customer:.* invoice_line_items:.*"},
        )
        sql_handler = SQLSelectSchemaQueryHandler(operation, schema_object, "postgres")

        log.info(f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}")

        assert (
            sql_handler.sql
            == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.total, i.last_updated, c.customer_id, c.first_name, c.last_name, c.company, c.address, c.city, c.state, c.country, c.postal_code, c.phone, c.fax, c.email, c.support_rep_id, c.version_stamp FROM invoice AS i INNER JOIN customer AS c ON i.customer_id = c.customer_id WHERE i.billing_state = %(i_billing_state)s"  # noqa E501
        )
        assert sql_handler.placeholders == {"i_billing_state": "FL"}

    def test_select_schema_handling_table(self, load_model):  # noqa F811
        schema_object = ModelFactory.get_schema_object("invoice")
        operation = Operation(
            operation_id="invoice",
            action="read",
            query_params={"billing_state": "FL"},
            metadata_params={"properties": ".* customer:.* invoice_line_items:.*"},
        )
        sql_handler = SQLSelectSchemaQueryHandler(operation, schema_object, "postgres")

        log.info(f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}")

        assert (
            sql_handler.sql
            == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.total, i.last_updated, c.customer_id, c.first_name, c.last_name, c.company, c.address, c.city, c.state, c.country, c.postal_code, c.phone, c.fax, c.email, c.support_rep_id, c.version_stamp FROM invoice AS i INNER JOIN customer AS c ON i.customer_id = c.customer_id WHERE i.billing_state = %(i_billing_state)s"  # noqa E501
        )
        assert sql_handler.placeholders == {"i_billing_state": "FL"}

    def test_select_simple_table(self, load_model):  # noqa F811
        try:
            sql_handler = SQLSelectSchemaQueryHandler(
                Operation(
                    operation_id="genre", action="read", query_params={"name": "Bill"}
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-af-engine": "postgres",
                        "x-af-database": "chinook",
                        "properties": {
                            "genre_id": {"type": "integer", "x-af-primary-key": "auto"},
                            "name": {"type": "string", "maxLength": 120},
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
                == "SELECT g.genre_id, g.name FROM genre AS g WHERE g.name = %(g_name)s"
            )
            assert sql_handler.placeholders == {"g_name": "Bill"}
        except ApplicationException as e:
            assert False, e.message

    def test_select_condition_with_count(self, load_model):  # noqa F811
        try:
            sql_handler = SQLSelectSchemaQueryHandler(
                Operation(
                    operation_id="genre",
                    action="read",
                    query_params={"genre_id": "gt::10"},
                    metadata_params={"count": True},
                ),
                SchemaObject(
                    "genre",
                    {
                        "x-af-engine": "postgres",
                        "x-af-database": "chinook",
                        "properties": {
                            "genre_id": {"type": "integer", "x-af-primary-key": "auto"},
                            "name": {"type": "string", "maxLength": 120},
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
                == "SELECT count(*) FROM genre AS g WHERE g.genre_id > %(g_genre_id)s"
            )
            assert sql_handler.placeholders == {"g_genre_id": 10}
        except ApplicationException as e:
            assert False, e.message

    def test_select_single_table_no_conditions(self, load_model):  # noqa F811
        try:
            sql_handler = SQLSelectSchemaQueryHandler(
                Operation(operation_id="genre", action="read"),
                SchemaObject(
                    "genre",
                    {
                        "x-af-engine": "postgres",
                        "x-af-database": "chinook",
                        "properties": {
                            "genre_id": {"type": "integer", "x-af-primary-key": "auto"},
                            "name": {"type": "string", "maxLength": 120},
                        },
                        "required": ["genre_id"],
                    },
                    ModelFactory.spec,
                ),
                "postgres",
            )
            log.info(
                f"sql-x: {sql_handler.sql}, placeholders: {sql_handler.placeholders}"  # noqa E501
            )

            assert sql_handler.sql == "SELECT g.genre_id, g.name FROM genre AS g"
            assert sql_handler.placeholders == {}

        except ApplicationException as e:
            assert False, e.message

    def test_delete(self, load_model):  # noqa F811
        schema_object = ModelFactory.get_schema_object("playlist_track")

        sql_handler = SQLDeleteSchemaQueryHandler(
            Operation(
                operation_id="playlist_track",
                action="delete",
                query_params={
                    "playlist_id": "2",
                },
                metadata_params={"_properties": "track_id"},
            ),
            schema_object,
            "postgres",
        )

        log.info(f"sql: {sql_handler.sql}, placeholders: {sql_handler.placeholders}")

        assert (
            sql_handler.sql
            == "DELETE FROM playlist_track WHERE playlist_id = %(playlist_id)s RETURNING track_id"  # noqa E501
        )
        assert sql_handler.placeholders == {"playlist_id": 2}

    def test_relation_search_condition(self, load_model):  # noqa F811
        operation = Operation(
            operation_id="invoice",
            action="read",
            query_params={"billing_state": "FL"},
            metadata_params={"properties": ".* customer:.* invoice_line_items:.*"},
        )
        schema_object = ModelFactory.get_schema_object("invoice")
        sql_handler = SQLSelectSchemaQueryHandler(operation, schema_object, "postgres")

        log.info(f"sql_handler: {sql_handler.sql}")
        assert (
            sql_handler.sql
            == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.total, i.last_updated, c.customer_id, c.first_name, c.last_name, c.company, c.address, c.city, c.state, c.country, c.postal_code, c.phone, c.fax, c.email, c.support_rep_id, c.version_stamp FROM invoice AS i INNER JOIN customer AS c ON i.customer_id = c.customer_id WHERE i.billing_state = %(i_billing_state)s"  # noqa E501
        )

        subselect_sql_generator = SQLSubselectSchemaQueryHandler(
            operation,
            schema_object.get_relation("invoice_line_items"),
            SQLSelectSchemaQueryHandler(operation, schema_object, "postgres"),
        )

        log.info(f"subselect_sql_generator: {subselect_sql_generator.sql}")
        assert (
            subselect_sql_generator.sql
            == "SELECT invoice_id, invoice_line_id, track_id, unit_price, quantity FROM invoice_line WHERE invoice_id IN ( SELECT invoice_id FROM invoice AS i WHERE i.billing_state = %(i_billing_state)s )"  # noqa E501
        )

        select_map = subselect_sql_generator.selection_result_map()
        log.info(f"select_map: {select_map}")

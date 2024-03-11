
from datetime import date

from api_maker.utils.model_factory import ModelFactory, SchemaObjectProperty
from api_maker.operation import Operation
from api_maker.dao.sql_generator import SQLGenerator
from api_maker.utils.logger import logger

log = logger(__name__)

class TestSQLGenerator():

  def test_field_selection(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(entity="invoice", action="read")

    sql_generator = SQLGenerator(operation, schema_object)

    log.info(f"prefix_map: {sql_generator.prefix_map}")
    log.info(f"result_map: {len(sql_generator.selection_result_map)}")
    assert len(sql_generator.selection_result_map) == 9

    operation = Operation(entity="invoice", action="read", metadata_params={"_properties": ".* line_items:.*"})
    sql_generator = SQLGenerator(operation, schema_object)

    log.info(f"result_map: {len(sql_generator.selection_result_map)}")
    assert len(sql_generator.selection_result_map) == 14
    log.info(f"select_list: {sql_generator.select_list}")

  def test_search_condition(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(entity="invoice", action="read",
                          query_params={"invoice_id": 24, "line_items.price": "gt:5"})

    sql_generator = SQLGenerator(operation, schema_object)
    log.info(f"search_condition: {sql_generator.search_condition}")

    assert False


  def test_search_value_assignment_type_relations(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(entity="invoice", action="read",
                          query_params={"invoice_id": 24, "line_items.price": "gt:5"})

    sql_generator = SQLGenerator(operation, schema_object)

    property = SchemaObjectProperty(
      engine="postgres",
      entity="invoice",
      name="invoice_id",
      properties={"type": "number", "format": "float"}
    )

    (sql, placeholders) = sql_generator.search_value_assignment("i", property, "1234")
    print( f"sql: {sql}, properties: {placeholders}")
    assert sql == "i.invoice_id = %(i_invoice_id)s"
    assert isinstance(placeholders["i_invoice_id"], float)

    # test greater than
    (sql, placeholders) = sql_generator.search_value_assignment("i", property, "gt:1234")
    print( f"sql: {sql}, properties: {placeholders}")
    assert sql == "i.invoice_id > %(i_invoice_id)s"
    assert isinstance(placeholders["i_invoice_id"], float)

    # test between
    (sql, placeholders) = sql_generator.search_value_assignment("i", property, "between:1200,1300")
    print( f"sql: {sql}, properties: {placeholders}")
    assert sql == "i.invoice_id BETWEEN %(i_invoice_id_1)s AND %(i_invoice_id_2)s"
    assert isinstance(placeholders["i_invoice_id_1"], float)
    assert placeholders["i_invoice_id_1"] == 1200.0
    assert placeholders["i_invoice_id_2"] == 1300.0

    # test in
    (sql, placeholders) = sql_generator.search_value_assignment("i", property, "in:1200,1250,1300")
    print( f"sql: {sql}, properties: {placeholders}")

    assert False

  def test_search_value_assignment_type_handling(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(entity="invoice", action="read",
                          query_params={"invoice_id": 24, "line_items.price": "gt:5"})

    sql_generator = SQLGenerator(operation, schema_object)

    property = SchemaObjectProperty(
      engine="postgres",
      entity="invoice",
      name="invoice_id",
      properties={"x-am-column-name": "x_invoice_id", "type": "string", "format": "date"}
    )

    (sql, placeholders) = sql_generator.search_value_assignment("i", property, "gt:2000-12-12")
    print( f"sql: {sql}, properties: {placeholders}")
    assert sql == "i.x_invoice_id > %(i_invoice_id)s"
    assert isinstance(placeholders["i_invoice_id"], date)
    assert placeholders["i_invoice_id"] == date(2000, 12, 12)

  def test_search_value_assignment(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(entity="invoice", action="read",
                          query_params={"invoice_id": 24, "line_items.price": "gt:5"})

    sql_generator = SQLGenerator(operation, schema_object)

    property = SchemaObjectProperty(
      engine="postgres",
      entity="invoice",
      name="last_updated",
      properties={"type": "string", "format": "date-time"}
    )

    (sql, placeholders) = sql_generator.search_value_assignment("i", property, "gt:2000-12-12")

    assert False
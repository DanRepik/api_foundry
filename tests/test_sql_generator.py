
from api_maker.utils.model_factory import ModelFactory
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

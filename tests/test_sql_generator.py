
from datetime import date, datetime, time, timezone

from api_maker.utils.app_exception import ApplicationException
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
                          query_params={"invoice_id": "24", "line_items.unit_price": "gt:5"})

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
    assert len(placeholders) == 2
    assert placeholders["i_invoice_id_1"] == 1200.0
    assert placeholders["i_invoice_id_2"] == 1300.0

    # test in
    (sql, placeholders) = sql_generator.search_value_assignment("i", property, "in:1200,1250,1300")
    print( f"sql: {sql}, properties: {placeholders}")
    assert sql == "i.invoice_id IN ( %(i_invoice_id_0)s, %(i_invoice_id_1)s, %(i_invoice_id_2)s)"
    assert isinstance(placeholders["i_invoice_id_1"], float)
    assert len(placeholders) == 3
    assert placeholders["i_invoice_id_0"] == 1200.0
    assert placeholders["i_invoice_id_1"] == 1250.0
    assert placeholders["i_invoice_id_2"] == 1300.0

  def test_search_value_assignment_column_rename(self):
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
    log.info( f"sql: {sql}, properties: {placeholders}")
    assert sql == "i.x_invoice_id > %(i_invoice_id)s"
    assert isinstance(placeholders["i_invoice_id"], date)
    assert placeholders["i_invoice_id"] == date(2000, 12, 12)

  def test_search_value_assignment_datetime(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(entity="invoice", action="read", query_params={"last-updated": date})

    sql_generator = SQLGenerator(operation, schema_object)

    # test date-time
    property = SchemaObjectProperty(
      engine="postgres",
      entity="invoice",
      name="last_updated",
      properties={"type": "string", "format": "date-time"}
    )

    (sql, placeholders) = sql_generator.search_value_assignment("i", property, "gt:2000-12-12T12:34:56Z")
    log.info( f"sql: {sql}, properties: {placeholders}")
    assert sql == "i.last_updated > %(i_last_updated)s"
    assert isinstance(placeholders["i_last_updated"], datetime)
    assert placeholders["i_last_updated"] == datetime(2000, 12, 12, 12, 34, 56, tzinfo=timezone.utc)

  def test_search_value_assignment_date(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(entity="invoice", action="read", query_params={"last-updated": date})
    sql_generator = SQLGenerator(operation, schema_object)

    property = SchemaObjectProperty(
      engine="postgres",
      entity="invoice",
      name="last_updated",
      properties={"type": "string", "format": "date"}
    )

    (sql, placeholders) = sql_generator.search_value_assignment("i", property, "gt:2000-12-12")
    log.info( f"sql: {sql}, properties: {placeholders}")
    assert sql == "i.last_updated > %(i_last_updated)s"
    assert isinstance(placeholders["i_last_updated"], date)
    assert placeholders["i_last_updated"] == date(2000, 12, 12)

    assert False

  def test_search_value_assignment_bool_to_int(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(entity="invoice", action="read", query_params={"is_active": "true"})
    sql_generator = SQLGenerator(operation, schema_object)

    property = SchemaObjectProperty(
      engine="postgres",
      entity="invoice",
      name="is_active",
      properties={"type": "boolean", "x-am-column-type": "integer"}
    )

    (sql, placeholders) = sql_generator.search_value_assignment("i", property, "true")
    log.info( f"sql: {sql}, properties: {placeholders}")
    assert sql == "i.is_active = %(i_is_active)s"
    assert isinstance(placeholders["i_last_updated"], date)
    assert placeholders["i_last_updated"] == date(2000, 12, 12)

    assert False

  def test_select_invalid_column(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(
      entity="invoice", 
      action="read", 
      query_params={"not_a_property": "FL"})

    try:
      sql_generator = SQLGenerator(operation, schema_object)
      log.info(f"sql: {sql_generator.sql}")
      assert False
    except ApplicationException as e:
      assert e.status_code == 500


  def test_select_single_table(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(
      entity="invoice", 
      action="read", 
      query_params={"billing_state": "FL"})
    sql_generator = SQLGenerator(operation, schema_object)

    log.info(f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}")

    assert sql_generator.sql == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.last_updated, i.total FROM chinook.invoice AS i WHERE i.billing_state = %(i_billing_state)s"
    assert sql_generator.placeholders == {'i_billing_state': 'FL'}

  def test_select_single_table_no_conditions(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(
      entity="invoice", 
      action="read")
    sql_generator = SQLGenerator(operation, schema_object)

    log.info(f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}")

    assert sql_generator.sql == "SELECT i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.last_updated, i.total FROM chinook.invoice AS i"
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
        "total": "1.63"
      })
    sql_generator = SQLGenerator(operation, schema_object)

    log.info(f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}")

    assert sql_generator.sql == "INSERT INTO chinook.invoice AS i ( i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_country, i.billing_postal_code, i.total ) VALUES ( i_customer_id, i_invoice_date, i_billing_address, i_billing_city, i_billing_country, i_billing_postal_code, i_total) RETURNING i.invoice_id, i.customer_id, i.invoice_date, i.billing_address, i.billing_city, i.billing_state, i.billing_country, i.billing_postal_code, i.last_updated, i.total"
    assert sql_generator.placeholders == {'i_customer_id': 2, 'i_invoice_date': datetime(2024, 3, 17, 0, 0), 'i_billing_address': 'Theodor-Heuss-Straße 34', 'i_billing_city': 'Stuttgart', 'i_billing_country': 'Germany', 'i_billing_postal_code': '70174', 'i_total': 1.63}
    
  def test_update(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(
      entity="invoice", 
      action="update",
      query_params={
        "customer_id": "2", 
      },
      store_params={
        "invoice_date": "2024-03-18", 
        "total": "2.63"
      },
      metadata_params={
        "_properties": "invoice_id last_updated"
      })
    sql_generator = SQLGenerator(operation, schema_object)

    log.info(f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}")

    assert sql_generator.sql == "UPDATE chinook.invoice AS i SET i.invoice_date = %(i_invoice_date)s, i.total = %(i_total)s WHERE i.customer_id = %(i_customer_id)s RETURNING i.invoice_id, i.last_updated"
    assert sql_generator.placeholders == {'i_customer_id': 2, 'i_invoice_date': datetime(2024, 3, 18, 0, 0), 'i_total': 2.63}
    
  def test_delete(self):
    schema_object = ModelFactory.get_schema_object("invoice")
    operation = Operation(
      entity="invoice", 
      action="delete",
      query_params={
        "customer_id": "2", 
      },
      metadata_params={
        "_properties": "invoice_id"
      })
    sql_generator = SQLGenerator(operation, schema_object)

    log.info(f"sql: {sql_generator.sql}, placeholders: {sql_generator.placeholders}")

    assert sql_generator.sql == "DELETE FROM chinook.invoice AS i WHERE i.customer_id = %(i_customer_id)s RETURNING i.invoice_id"
    assert sql_generator.placeholders == {'i_customer_id': 2}
    

from typing import Any
from api_maker.utils.logger import logger
from api_maker.operation import Operation
from api_maker.utils.model_factory import ModelFactory, SchemaObject, SchemaObjectProperty

log = logger(__name__)

class SQLGenerator:
  def __init__(self, operation: Operation) -> None:
      self.operation = operation
      self.field_map = self.get_field_map(operation)

  def __get_field_map(self, operation: Operation) -> dict[str, Any]:
      result = dict()

      return result

  def select(self, schema_object: SchemaObject) -> list:

        if "_count" in operation.query_params:
            result = self.count_sql(operation, schema_object)
        else:
            result = self.select_sql(operation, schema_object)
        log.debug(f"dao select result: {result}")
        return result

  def insert(self, operation: Operation, schema_object: SchemaObject) -> tuple[str, dict]:
        result = self.__insert_sql(operation, schema_object)
        log.debug(f"dao insert result: {result}")
        return result

  def __insert_sql(self, operation: Operation, schema_object: SchemaObject) -> tuple[str, dict]:
      (insert_columns, placeholders, insert_values) = self._get_insert_parts(**args)
      result_fields = self._get_results_map(**args)
      result_columns = [field[3] for field in result_fields]

      return f"INSERT INTO {schema_object.table_name} ({', '.join(insert_columns)}) VALUES ({', '.join(placeholders)}) RETURNING {', '.join(result_columns)}"

  def _get_insert_parts(self, operation: Operation, schema_object: SchemaObject) -> tuple[list[str], list[str], dict]:
      # remove the timestamp column if it exists
      if self.timestamp_field in filtered_fields:
          filtered_fields.remove(self.timestamp_field)

      # build the columns and values for the insert
      columns = []
      placeholders = []
      values = {}
      for property_name, value in operation.store_params.items():
          property = schema_object.get_property(property_name)
          columns.append(property.column_name)
          column_type = self._get_column_type(field_name)
          placeholders.append(self._placeholder(field_name, column_type))
          values[field_name] = self._change_type(
              store_parameters[field_name], column_type
          )

      # add the timestamp column and set it to now
      if self.timestamp_field is not None:
          columns.append(self._alias_field(self.timestamp_field))
          placeholders.append(self._timestamp_function())

      log.debug(f"columns: {columns}, placeholders: {placeholders}")

      return (columns, placeholders, values)


  def update(self, operation: Operation, schema_object: SchemaObject) -> tuple[str, dict]:
        result = self.update_sql(operation, schema_object)
        log.debug(f"dao update result: {result}")
        return result

  def update_sql(self, operation: Operation, schema_object: SchemaObject) -> tuple[str, dict]:
      (assignments, arguments) = self._get_update_parts(**args)
      result_fields = self._get_results_map(**args)
      result_columns = [field[3] for field in result_fields]
      (query_conditions, query_parameters) = self._get_query_conditions(**args)

      return (f"UPDATE {schema_object.table_name} SET {', '.join(assignments)} {self._where_condition(query_conditions)} RETURNING {', '.join(result_columns)}", query_parameters)

  def delete(self, operation: Operation, schema_object: SchemaObject) -> tuple[str, dict]:
        result = self.delete_sql(operation, schema_object)
        log.debug(f"dao delete result: {result}")
        return result


  def delete_sql(self, operation: Operation, schema_object: SchemaObject) -> tuple[str, dict]:
      schema_object = ModelFactory.get_schema_object(operation.entity)
      (query_conditions, query_parameters) = self._get_query_conditions(operation, schema_object)
      result_fields = self._get_results_map(**args)
      result_columns = [field[3] for field in result_fields]

      return f"DELETE FROM {self._full_table_name()} {self._where_condition(query_conditions)} RETURNING {', '.join(result_columns)}"

  # build the where section of an SQL statement
  # Returns the condition string with placeholders
  # and a dictionary mapping placeholders to values.
  # When usePrefix is true column references and
  # placeholders are prefixed
  def _get_query_conditions(self, operation: Operation, schema_object: SchemaObject) -> tuple[list[str], set]:

      if operation.query_params is None:
          return ([], set())

      key_set = {}

      assignments = []
      for field_name, value in operation.query_params.items():
          cardinality = "1:1"
          field_parts = field_name.split(".")
          if len(field_parts) > 1:
              entity = field_parts[0]
              field_name = field_parts[1]
              relation = self.relations[entity]
              dao = relation["dao"]
              cardinality = relation["cardinality"]

          if cardinality == "1:1":
              dao._append_assignment(
                  assignments,
                  key_set,
                  field_name,
                  value,
                  args.get("use_prefix", False),
              )

        if len(assignments) == 0:
            return ([], {})

        return (assignments, key_set)

  def _append_assignment(
      self,
      assignments: list[str],
      key_set: dict[str, Any],
      property_name: str,
      values: str,
      use_prefix: bool,
  ):

        column_type = self._get_column_type(field_name)
        param_str = f"q_{self.prefix}_{field_name}" if use_prefix else field_name

        operand = "="
        if isinstance(values, str):
            if values.startswith("lt:"):
                operand = "<"
                values = values[3:]
            elif values.startswith("le:"):
                operand = "<="
                values = values[3:]
            elif values.startswith("ne:"):
                operand = "<>"
                values = values[3:]
            elif values.startswith("eq:"):
                operand = "="
                values = values[3:]
            elif values.startswith("ge:"):
                operand = ">="
                values = values[3:]
            elif values.startswith("gt:"):
                operand = ">"
                values = values[3:]
            elif values.startswith("like:"):
                operand = "LIKE"
                values = values[3:].replace("*", "%")
            elif values.startswith("between:"):
                value_set = values[8:].split(",")
                key_set[f"{param_str}_1"] = self._to_parameter_value(
                    field_name, value_set[0]
                )
                key_set[f"{param_str}_2"] = self._to_parameter_value(
                    field_name, value_set[1]
                )
                assignments.append(
                    f"{self._get_column_name(field_name, use_prefix)} "
                    + f"BETWEEN {self._placeholder(param_str + '_1', column_type)} "
                    + f"AND {self._placeholder(param_str + '_2', column_type)}"
                )
                return
            elif values.startswith("not-between:"):
                value_set = values[12:].split(",")
                key_set[f"{param_str}_1"] = self._to_parameter_value(
                    field_name, value_set[0]
                )
                key_set[f"{param_str}_2"] = self._to_parameter_value(
                    field_name, value_set[1]
                )
                assignments.append(
                    f"{self._get_column_name(field_name, use_prefix)} "
                    + f"NOT BETWEEN {self._placeholder(param_str + '_1', column_type)} "
                    + f"AND {self._placeholder(param_str + '_2', column_type)}"
                )
                return
            elif values.startswith("in:"):
                value_set = values[3:].split(",")

                assignment = []
                index = 0
                for item in value_set:
                    key_set[f"{param_str}_{index}"] = self._to_parameter_value(
                        field_name, item
                    )
                    assignment.append(
                        self._placeholder(f"{param_str}_{index}", column_type)
                    )
                    index += 1

                assignments.append(
                    f"{self._get_column_name(field_name, use_prefix)} "
                    + f"IN ({', '.join(assignment)})"
                )
                return
            elif values.startswith("not-in:"):
                value_set = values[7:].split(",")

                assignment = []
                index = 0
                for item in value_set:
                    key_set[f"{param_str}_{index}"] = self._to_parameter_value(
                        field_name, item
                    )
                    assignment.append(
                        self._placeholder(f"{param_str}_{index}", column_type)
                    )
                    index += 1

                assignments.append(
                    f"{self._get_column_name(field_name, use_prefix)} "
                    + f"NOT IN ({', '.join(assignment)})"
                )
                return

        key_set[param_str] = self._to_parameter_value(field_name, values)
        assignments.append(
            f"{self._get_column_name(field_name, use_prefix)} {operand} {self._placeholder(param_str, column_type)}"
        )

  def divide_by_entity(self, dictionary: dict):
      """
      Divide a dictionary into separate maps for each entity and the default entity.

      Parameters:
      - dictionary (dict): The input dictionary.

      Returns:
      - tuple: A tuple containing two dictionaries.
              The first set contains keys with the default entity.
              The second dictionary contains sets of keys divided by entity.
      """
      default_entity_map = set()
      entity_maps = dict()

      for key, in dictionary.keys():
          parts = key.split('.')
          if len(parts) == 1:
              default_entity_map.add(key)
          else:
              entity = parts[0]
              property_name = parts[1]
              if entity not in entity_maps:
                  entity_maps[entity] = set()
              entity_maps[entity].add(property_name)

      return default_entity_map, entity_maps

  def _get_results_map(self, operation: Operation, schema_object: SchemaObject) -> list:
      # set up the returning columns set
      fields = []

      for property_name, property in schema_object.properties.items():
          if property.type is not None:
              # field_type is not None only when column type is None
              # (avoids unnecessary conversions)
              field_type = self.fields[field_name].get("type")
              bind_type = column_type
          else:
              field_type = None
              bind_type = self.fields[field_name].get("type")

          column_name = self._alias_field(field_name)
          fields.append(
              {
                  "entity": "default",
                  "name": field_name,
                  "type": field_type,
                  "column_name": column_name,
                  "cardinality": "1:1",
                  "bind_type": bind_type,
              }
          )

      return fields

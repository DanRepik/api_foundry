import re

from typing import Any
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.operation import Operation
from api_maker.utils.model_factory import (
    ModelFactory,
    SchemaObject,
    SchemaObjectProperty,
)

log = logger(__name__)


class SQLGenerator:
    def __init__(self, operation: Operation, schema_object: SchemaObject) -> None:
        self.operation = operation
        self.schema_object = schema_object
        self.prefix_map = self.__get_prefix_map(schema_object)
        self.single_table = self.__single_table()
        self.__select_list = None
        self.__select_list_columns = None
        self.__select_list_map = None
        self.search_placeholders = {}
        self.store_placeholders = {}

    def __single_table(self):
        if len(self.prefix_map) == 1 or self.operation.action == "create":
            return True
        
        if ":" in self.operation.metadata_params.get("_properties", ""):
            return False

        for param in self.operation.query_params.keys():
            if "." in param:
                return False

        return True

    @property
    def sql(self) -> str:
        action_sql_map = {
            "read": f"SELECT {self.select_list} FROM {self.table_expression}{self.search_condition}",
            "create": f"INSERT INTO {self.table_expression}{self.insert_values} RETURNING {self.select_list}",
            "update": f"UPDATE {self.table_expression}{self.update_values}{self.search_condition} RETURNING {self.select_list}",
            "delete": f"DELETE FROM {self.table_expression}{self.search_condition} RETURNING {self.select_list}"
        }
        sql = action_sql_map.get(self.operation.action)
        if sql is None:
            raise ApplicationException(500, f"Invalid operation action: {self.operation.action}")
        return sql
    
    @property
    def placeholders(self) -> dict:
        return {**self.search_placeholders, **self.store_placeholders}

    def __get_prefix_map(self, schema_object: SchemaObject):
        result = {"$default$": schema_object.entity[:1]}

        for entity in schema_object.relations.keys():
            for i in range(1, len(entity) + 1):
                substring = entity[:i]
                if substring not in result.values():
                    result[entity] = substring
                    break

        log.info(f"prefix_map: {result}")
        return result
    
    @property
    def select_list_columns(self) -> list[str]:
        if not self.__select_list_columns:
            self.__select_list_columns = self.selection_result_map.keys()
        return self.__select_list_columns

    @property
    def select_list(self) -> str:
        if not self.__select_list:
            self.__select_list = ", ".join(self.select_list_columns)
        return self.__select_list
    
    @property
    def result_fields(self) -> dict[str, SchemaObjectProperty]:
        log.info(f"select_list: {self.select_list}")
        log.info(f"select_result_map: {self.selection_result_map}")
        result = {}
        for column in self.select_list_columns:
            log.info(f"column: {column}")
            result[column] = self.selection_result_map[column]
        return result;

    @property
    def table_expression(self) -> str:
        if self.single_table:
            return self.schema_object.table_name

        joins = []
        parent_prefix = self.prefix_map["$default$"]
        for name, relation in self.schema_object.relations.items():
            log.info(f"relation name: {name}, relation: {vars(relation)}")
            child_prefix = self.prefix_map[relation.name]
            if relation.cardinality == "single":
                table_expression = (
                    f"{relation.schema_object.table_name} AS {child_prefix}"
                )
                joins.append(
                    f"INNER JOIN {table_expression} ON {parent_prefix}.{relation.parent_property} = {child_prefix}.{relation.child_property.column_name}"
                )

        inner_join = f" {' '.join(joins)}" if len(joins) > 0 else ""
        log.debug(f"inner_join: {inner_join}")
        return f"{self.schema_object.table_name} AS {self.prefix_map['$default$']}{inner_join}"

    @property
    def search_condition(self) -> str:
        log.info(f"query_params: {self.operation.query_params}")

        self.search_placeholders = {}
        conditions = []

        log.info("building search conditions")

        for name, value in self.operation.query_params.items():
            parts = name.split(".")
            log.info(f"parts: {parts}")

            try:
                if len(parts) > 1:
                    relation = self.schema_object.relations[parts[0]]
                    property = relation.schema_object.properties[parts[1]]
                    prefix = self.prefix_map[parts[0]]
                else:
                    property = self.schema_object.properties[parts[0]]
                    prefix = self.prefix_map["$default$"]
            except KeyError:
                raise ApplicationException(
                    500, f"Search condition column not found {name}"
                )

            log.info(f"name: {name}, value: {value}, prefix: {prefix}")
            assignment, holders = self.search_value_assignment(prefix, property, value)
            log.info(f"assignment; {assignment}, holders: {holders}")
            conditions.append(assignment)
            self.search_placeholders.update(holders)

        log.info(f"conditions: {conditions}")
        return f" WHERE {' AND '.join(conditions)}" if len(conditions) > 0 else ""

    @property
    def insert_values(self) -> str:
        log.info(f"insert_values store_params: {self.operation.store_params}")

        self.store_placeholders = {}
        placeholders = []
        columns = []

        for name, value in self.operation.store_params.items():
            parts = name.split(".")
            log.info(f"parts: {parts}")

            try:
                if len(parts) > 1:
                    raise ApplicationException(
                        400, f"Properties can not be set on related objects {name}"
                    )

                property = self.schema_object.properties[parts[0]]
            except KeyError:
                raise ApplicationException(
                    400, f"Search condition column not found {name}"
                )

            log.info(f"name: {name}, value: {value}")
            columns.append(property.column_name)
            placeholders.append(property.name)
            self.store_placeholders[property.name] = property.convert_to_db_value(value)

        return f" ( {', '.join(columns)} ) VALUES ( {', '.join(placeholders)})"

    @property
    def update_values(self) -> str:
        log.info(f"update_values store_params: {self.operation.store_params}")

        prefix = self.prefix_map["$default$"]
        self.store_placeholders = {}
        columns = []

        for name, value in self.operation.store_params.items():
            parts = name.split(".")
            log.info(f"parts: {parts}")

            try:
                if len(parts) > 1:
                    raise ApplicationException(
                        400, f"Properties can not be set on related objects {name}"
                    )

                property = self.schema_object.properties[parts[0]]
            except KeyError:
                raise ApplicationException(
                    400, f"Search condition column not found {name}"
                )

            log.info(f"name: {name}, value: {value}, prefix: {prefix}")

            if self.single_table:
                placeholder = property.name
                column_name = property.column_name
            else:
                placeholder = f"{prefix}_{property.name}"
                column_name = f"{prefix}.{property.column_name}"

            columns.append(f"{column_name} = {self.placeholder(property, placeholder)}")
            self.store_placeholders[placeholder] = property.convert_to_db_value(value)

        return f" SET {', '.join(columns)}"

    def search_value_assignment(
        self, prefix: str, property: SchemaObjectProperty, value_str
    ) -> tuple[str, dict]:
        log.info(f"prefix: {prefix}, property: {vars(property)}, value_str: {value_str}")
        operand = "="

        relational_types = {
            "lt": "<",
            "le": "<=",
            "eq": "=",
            "ge": ">=",
            "gt": ">",
            "in": "in",
            "not-in": "not-in",
            "between": "between",
            "not-between": "not-between",
        }

        parts = value_str.split(":", 1)
        operand = relational_types[parts[0] if len(parts) > 1 else "eq"]
        value_str = parts[-1]

        log.info(
            f"operand: {operand}, column: {property.column_name}, value_str: {value_str}"
        )
        column = (
            property.column_name
            if self.single_table
            else f"{prefix}.{property.column_name}"
        )

        if operand in ["between", "not-between"]:
            value_set = value_str.split(",")
            log.info(f"value_set: {value_set}")
            placeholder_name = (
                property.name if self.single_table else f"{prefix}_{property.name}"
            )
            sql = (
                "NOT "
                if operand == "not-between"
                else ""
                + f"{column} "
                + f"BETWEEN {self.placeholder(property, f'{placeholder_name}_1')} "
                + f"AND {self.placeholder(property, f'{placeholder_name}_2')}"
            )
            placeholders = {
                f"{placeholder_name}_1": property.convert_to_db_value(value_set[0]),
                f"{placeholder_name}_2": property.convert_to_db_value(value_set[1]),
            }

        elif operand in ["in", "not-in"]:
            value_set = value_str.split(",")
            assigments = []
            placeholder_name = (
                property.name if self.single_table else f"{prefix}_{property.name}"
            )
            placeholders = {}
            index = 0
            for item in value_set:
                item_name = f"{placeholder_name}_{index}"
                placeholders[item_name] = property.convert_to_db_value(item)
                assigments.append(self.placeholder(property, item_name))
                index += 1

            sql = (
                "NOT "
                if operand == "not-in"
                else "" + f"{column} IN ( {', '.join(assigments)}" + ")"
            )

        else:
            placeholder_name = (
                property.name if self.single_table else f"{prefix}_{property.name}"
            )
            placeholder = self.placeholder(property, f"{placeholder_name}")
            sql = f"{column} {operand} {placeholder}"
            placeholders = {
                f"{placeholder_name}": property.convert_to_db_value(value_str)
            }

        log.debug(f"placeholders: {placeholders}")
        return sql, placeholders

    @property
    def selection_result_map(self) -> dict:
        if not self.__select_list_map:
            filter_str = self.operation.metadata_params.get("_properties", "")
            log.info(f"Filter string: {filter_str}")
            self.__select_list_map = {}

            if not filter_str:
                filter_str = ".*"

            log.info(f"Building map; {self.get_regex_map(filter_str)}")
            for relation, reg_exs in self.get_regex_map(filter_str).items():
                log.info(f"relation: {relation}, reg_exs: {reg_exs}")

                # Extract the schema object for the current entity
                relation_property = self.schema_object.relations.get(relation)


                if relation_property:
                    if relation_property.cardinality != 'single':
                        continue

                    log.info(f"relation_property: {relation_property.cardinality}")
                    # Use a default value if relation_property is None
                    schema_object = relation_property.schema_object
                else:
                    schema_object = self.schema_object

                log.info(f"schema_object: {schema_object.entity}")

                # Filter and prefix keys for the current entity and regular expressions
                filtered_keys = self.filter_and_prefix_keys(
                    self.prefix_map[relation], reg_exs, schema_object.properties
                )
                log.info(f"filtered_keys: {filtered_keys}")

                # Extend the result map with the filtered keys
                self.__select_list_map.update(filtered_keys)

        log.info(f"__select_list_map: {self.__select_list_map}")
        return self.__select_list_map
    
    def marshal_record(self, record) -> dict:
        object_set = {}
        for name, value in record.items():
            property = self.selection_result_map[name]
            parts = name.split('.')
            log.info(f"name: {name}, value: {value}, type: {type(value)}, parts: {parts}")
            if len(parts) > 1:
                object = object_set.get(parts[0], {})
                if not object:
                    object_set[parts[0]] = object
                object[property.name] = property.convert_to_api_value(value)

        log.info(f"prefix_map: {self.prefix_map}")
        result = object_set[self.prefix_map["$default$"]]
        for name, prefix in self.prefix_map.items():
            log.info(f"name: {name}, prefix: {prefix}")
            if name != "$default$" and prefix in object_set:
                result[name] = object_set[prefix]

        return result

    def filter_and_prefix_keys(
        self, prefix: str, regex_list: list[str], properties: dict
    ):
        """
        Accepts a prefix string, list of regular expressions, and a dictionary.
        Returns a new dictionary containing items whose keys match any of the regular expressions,
        with the prefix string prepended to the key values of the dictionary.

        Parameters:
        - prefix (str): The prefix string to prepend to the key values.
        - regex_list (list of str): The list of regular expression patterns to match keys.
        - properties (dict): The input properties.

        Returns:
        - dict: A new dictionary containing filtered items with modified key values.
        """
        log.info(
            f"prefix: {prefix}, regex_list: {regex_list}, properties: {properties}"
        )
        filtered_dict = {}

        # Compile the regular expression patterns
        compiled_regexes = [re.compile(regex) for regex in regex_list]

        # Iterate over the items in the input properties
        for key, value in properties.items():
            # Check if the key matches any of the regular expression patterns
            for pattern in compiled_regexes:
                if pattern.match(key):
                    # Prepend the prefix to the key value and add it to the new dictionary
                    if self.single_table:
                        filtered_dict[key] = value
                    else:
                        filtered_dict[f"{prefix}.{key}"] = value
                    break

        log.info(f"filtered: {filtered_dict}")
        return filtered_dict

    def get_regex_map(self, filter_str: str) -> dict[str, list]:
        result = {}

        for filter in filter_str.split():
            parts = filter.split(":")
            entity = parts[0] if len(parts) > 1 else "$default$"
            expression = parts[-1]

            # Check if entity already exists in result, if not, initialize it with an empty list
            if entity not in result:
                result[entity] = []

            # Append the expression to the list of expressions for the entity
            result[entity].append(expression)

        return result

    def placeholder(self, property: SchemaObjectProperty, param: str) -> str:
        if property.engine == "oracle":
            if property.column_type == "date":
                return f"TO_DATE(:{param}, 'YYYY-MM-DD')"
            elif property.column_type == "datetime":
                return f"TO_TIMESTAMP(:{param}, 'YYYY-MM-DD\"T\"HH24:MI:SS.FF')"
            elif property.column_type == "time":
                return f"TO_TIME(:{param}, 'HH24:MI:SS.FF')"
            return f":{param}"
        return f"%({param})s"

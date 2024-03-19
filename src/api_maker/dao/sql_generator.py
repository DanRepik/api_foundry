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
        self.__select_list_map = None
        self.search_placeholders = {}
        self.store_placeholders = {}

    @property
    def sql(self) -> str:
        if self.operation.action == 'read':
            return f"SELECT {self.select_list} FROM {self.table_expression}{self.search_condition}"
        elif self.operation.action == "create":
            return f"INSERT INTO {self.table_expression}{self.insert_values} RETURNING {self.select_list}"
        elif self.operation.action == "update":
            return f"UPDATE {self.table_expression}{self.update_values}{self.search_condition} RETURNING {self.select_list}"
        elif self.operation.action == "delete":
            return f"DELETE FROM {self.table_expression}{self.search_condition} RETURNING {self.select_list}"
        
        raise ApplicationException(500, f"Invalid operation action: {self.operation.action}")

    @property
    def placeholders(self) -> dict:
        return { **self.search_placeholders, **self.store_placeholders}

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
    def select_list(self) -> str:
        return ", ".join(self.selection_result_map.keys())

    @property
    def table_expression(self) -> str:
        return f"{self.schema_object.table_name} AS {self.prefix_map['$default$']}" 

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
                raise ApplicationException( 500, f"Search condition column not found {name}")

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

        prefix = self.prefix_map["$default$"]
        self.store_placeholders = {}
        placeholders = []
        columns = []

        for name, value in self.operation.store_params.items():
            parts = name.split(".")
            log.info(f"parts: {parts}")

            try:
                if len(parts) > 1:
                    raise ApplicationException( 400, f"Properties can not be set on related objects {name}")

                property = self.schema_object.properties[parts[0]]
            except KeyError:
                raise ApplicationException( 400, f"Search condition column not found {name}")

            log.info(f"name: {name}, value: {value}, prefix: {prefix}")
            columns.append(f"{prefix}.{property.column_name}")
            placeholder = f"{prefix}_{property.name}"
            placeholders.append(placeholder)
            self.store_placeholders[placeholder] = property.convert_to_db_value(value)
        
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
                    raise ApplicationException( 400, f"Properties can not be set on related objects {name}")

                property = self.schema_object.properties[parts[0]]
            except KeyError:
                raise ApplicationException( 400, f"Search condition column not found {name}")

            log.info(f"name: {name}, value: {value}, prefix: {prefix}")
            placeholder = f"{prefix}_{property.name}"
            columns.append(f"{prefix}.{property.column_name} = {self.placeholder(property, placeholder)}")
            self.store_placeholders[placeholder] = property.convert_to_db_value(value)
        
        return f" SET {', '.join(columns)}"
        
    def search_value_assignment(
        self, prefix: str, property: SchemaObjectProperty, value_str: str
    ) -> tuple[str, dict]:
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
        column = f"{prefix}.{property.column_name}"

        if operand in ["between", "not-between"]:
            value_set = value_str.split(",")
            log.info(f"value_set: {value_set}")
            sql = (
                "NOT "
                if operand == "not-between"
                else ""
                + f"{column} "
                + f"BETWEEN {self.placeholder(property, f'{prefix}_{property.name}_1')} "
                + f"AND {self.placeholder(property, f'{prefix}_{property.name}_2')}"
            )
            placeholders = {
                f"{prefix}_{property.name}_1": property.convert_to_db_value(
                    value_set[0]
                ),
                f"{prefix}_{property.name}_2": property.convert_to_db_value(
                    value_set[1]
                ),
            }

        elif operand in ["in", "not-in"]:
            value_set = value_str.split(",")
            assigments = []
            placeholders = {}
            index = 0
            for item in value_set:
                item_name = f"{prefix}_{property.name}_{index}"
                placeholders[item_name] = property.convert_to_db_value(item)
                assigments.append(self.placeholder(property, item_name))
                index += 1

            sql = (
                "NOT "
                if operand == "not-in"
                else "" + f"{column} IN ( {', '.join(assigments)}" + ")"
            )

        else:
            placeholder = self.placeholder(property, f"{prefix}_{property.name}")
            sql = f"{column} {operand} {placeholder}"
            placeholders = {
                f"{prefix}_{property.name}": property.convert_to_db_value(value_str)
            }

        log.debug(f"placeholders: {placeholders}")
        return sql, placeholders

    @property
    def selection_result_map(self) -> dict:
        if not self.__select_list_map:
            log.info("Building map")
            filter_str = self.operation.metadata_params.get("_properties", "")
            log.info(f"Filter string: {filter_str}")
            self.__select_list_map = {}

            if not filter_str:
                filter_str = ".*"

            for relation, reg_exs in self.get_regex_map(filter_str).items():

                # Extract the schema object for the current entity
                relation_property = self.schema_object.relations.get(relation)

                # Use a default value if relation_property is None
                schema_object = (
                    relation_property.schema_object
                    if relation_property
                    else self.schema_object
                )
                log.info(f"schema_object: {schema_object.entity}")

                # Filter and prefix keys for the current entity and regular expressions
                filtered_keys = self.filter_and_prefix_keys(
                    self.prefix_map[relation], reg_exs, schema_object.properties
                )
                log.info(f"filtered_keys: {filtered_keys}")

                # Extend the result map with the filtered keys
                self.__select_list_map.update(filtered_keys)

        return self.__select_list_map

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


import re

from typing import Any
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
        self.__search_condition_map = None

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
    def search_condition(self) -> str:
        log.info(f"query_params: {self.operation.query_params}")
        return "AND ".join(self.search_condition_map().keys())

    def search_condition_map(self) -> dict:
        if not self.__search_condition_map:
            log.info("building search conditions")
            self.__search_condition_map = {}

            for name, value in self.operation.query_params.items():
                parts = name.split(".")
                log.info(f"parts: {parts}")
                if len(parts) > 1:
                    entity = self.prefix_map[parts[0]] 
                else:
                    entity = self.schema_object.entity
                log.info(f"name: {name}, value: {value}, entity: {entity}")

        return self.__search_condition_map

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
                schema_object = relation_property.schema_object if relation_property else self.schema_object
                log.info(f"schema_object: {schema_object.entity}")

                # Filter and prefix keys for the current entity and regular expressions
                filtered_keys = self.filter_and_prefix_keys(self.prefix_map[relation], reg_exs, schema_object.properties)
                log.info(f"filtered_keys: {filtered_keys}")

                # Extend the result map with the filtered keys
                self.__select_list_map.update(filtered_keys)

        return self.__select_list_map


    def filter_and_prefix_keys(
        self, prefix: str, regex_list: list[str], dictionary: dict
    ):
        """
        Accepts a prefix string, list of regular expressions, and a dictionary.
        Returns a new dictionary containing items whose keys match any of the regular expressions,
        with the prefix string prepended to the key values of the dictionary.

        Parameters:
        - prefix (str): The prefix string to prepend to the key values.
        - regex_list (list of str): The list of regular expression patterns to match keys.
        - dictionary (dict): The input dictionary.

        Returns:
        - dict: A new dictionary containing filtered items with modified key values.
        """
        log.info(
            f"prefix: {prefix}, regex_list: {regex_list}, dictionary: {dictionary}"
        )
        filtered_dict = {}

        # Compile the regular expression patterns
        compiled_regexes = [re.compile(regex) for regex in regex_list]

        # Iterate over the items in the input dictionary
        for key, value in dictionary.items():
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

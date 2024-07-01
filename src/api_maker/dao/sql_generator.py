import re
from typing import Optional
from datetime import datetime, date

from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.operation import Operation
from api_maker.utils.model_factory import SchemaObject, SchemaObjectProperty

log = logger(__name__)


class SQLGenerator:
    operation: Operation
    schema_object: SchemaObject
    engine: str

    def __init__(
        self, operation: Operation, schema_object: SchemaObject, engine: str
    ) -> None:
        self.operation = operation
        self.schema_object = schema_object
        self.engine = engine
        self.prefix_map = self.__get_prefix_map(schema_object)
        self.single_table = self.__single_table()
        self.__select_list = None
        self.__select_list_columns = None
        self.__selection_result_map = None
        self.search_placeholders = dict()
        self.store_placeholders = dict()
        self.active_prefixes = set()

    @property
    def sql(self) -> str:
        raise NotImplementedError

    @property
    def selection_results(self):
        if not self.__selection_result_map:
            self.__selection_result_map = self.selection_result_map()
        return self.__selection_result_map

    def __single_table(self):
        if len(self.prefix_map) == 1 or self.operation.action == "create":
            return True

        if ":" in self.operation.metadata_params.get("properties", ""):
            return False

        for param in self.operation.query_params.keys():
            if "." in param:
                return False

        return True

    @property
    def placeholders(self) -> dict:
        log.debug(f"search placeholders: {self.search_placeholders}")
        return {**self.search_placeholders, **self.store_placeholders}

    def __get_prefix_map(self, schema_object: SchemaObject):
        result = {"$default$": schema_object.entity[:1]}

        for entity in schema_object.relations.keys():
            for i in range(1, len(entity) + 1):
                substring = entity[:i]
                if substring not in result.values():
                    result[entity] = substring
                    break

        log.debug(f"prefix_map: {result}")
        return result

    @property
    def select_list_columns(self) -> list[str]:
        if not self.__select_list_columns:
            self.__select_list_columns = list(self.selection_results.keys())
        return self.__select_list_columns

    @property
    def select_list(self) -> str:
        if not self.__select_list:
            self.__select_list = ", ".join(self.select_list_columns)
        return self.__select_list

    @property
    def table_expression(self) -> str:
        return self.schema_object.table_name

    @property
    def search_condition(self) -> str:
        log.debug(f"query_params: {self.operation.query_params}")

        self.search_placeholders = {}
        conditions = []

        for name, value in self.operation.query_params.items():
            if "." in name:
                raise ApplicationException(
                    400, "Selection on relations is not supported"
                )

            try:
                property = self.schema_object.properties[name]
            except KeyError:
                raise ApplicationException(
                    500, f"Search condition column not found {name}"
                )

            assignment, holders = self.search_value_assignment(property, value)
            conditions.append(assignment)
            self.search_placeholders.update(holders)

        return f" WHERE {' AND '.join(conditions)}" if len(conditions) > 0 else ""

    def search_value_assignment(
        self, property: SchemaObjectProperty, value, prefix: Optional[str] = None
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

        if isinstance(value, str):
            parts = value.split("::", 1)
            if parts[0] in relational_types:
                operand = relational_types[parts[0] if len(parts) > 1 else "eq"]
                value_str = parts[-1]
            else:
                value_str = value
        elif isinstance(value, datetime):
            value_str = datetime.isoformat(value)
        elif isinstance(value, date):
            value_str = date.isoformat(value)
        else:
            value_str = str(value)

        column = f"{prefix}.{property.column_name}" if prefix else property.column_name
        placeholder_name = f"{prefix}_{property.name}" if prefix else property.name

        if operand in ["between", "not-between"]:
            value_set = value_str.split(",")
            placeholder_name = (
                property.name if self.single_table else f"{prefix}_{property.name}"
            )
            sql = (
                column
                + (" NOT " if operand == "not-between" else " ")
                + (
                    "BETWEEN "
                    + self.placeholder(property, f"{placeholder_name}_1")
                    + " AND "
                    + self.placeholder(property, f"{placeholder_name}_2")
                )
            )

            placeholders = {
                f"{placeholder_name}_1": property.convert_to_db_value(value_set[0]),
                f"{placeholder_name}_2": property.convert_to_db_value(value_set[1]),
            }

        elif operand in ["in", "not-in"]:
            value_set = value_str.split(",")
            assigments = []
            placeholders = {}
            index = 0
            for item in value_set:
                item_name = f"{placeholder_name}_{index}"
                placeholders[item_name] = property.convert_to_db_value(item)
                assigments.append(self.placeholder(property, item_name))
                index += 1

            sql = (
                column
                + (" NOT " if operand == "not-in" else " ")
                + (f"IN ({', '.join(assigments)})")
            )

        else:
            sql = f"{column} {operand} " + self.placeholder(property, placeholder_name)
            placeholders = {
                f"{placeholder_name}": property.convert_to_db_value(value_str)
            }

        if (
            self.operation.action != "read"
            and operand != "="
            and self.schema_object.concurrency_property
        ):
            raise ApplicationException(
                400,
                "Concurrency settings prohibit multi-record updates "
                + self.schema_object.entity
                + ", property: "
                + property.name,
            )
        self.active_prefixes.add(prefix)
        return sql, placeholders

    def selection_result_map(self) -> dict:
        if not self.__selection_result_map:
            filters = self.operation.metadata_params.get("_properties", ".*").split()

            # Filter and prefix keys for the current entity and regular
            # expressions
            self.__selection_result_map = self.filter_and_prefix_keys(
                filters, self.schema_object.properties
            )

        return self.__selection_result_map

    def marshal_record(self, record) -> dict:
        result = {}
        for name, value in record.items():
            property = self.selection_results[name]
            result[property.name] = property.convert_to_api_value(value)

        return result

    def filter_and_prefix_keys(
        self,
        regex_list: list[str],
        properties: dict,
        prefix: Optional[str] = None,
    ):
        """
        Accepts a prefix string, list of regular expressions, and a
        dictionary.
        Returns a new dictionary containing items whose keys match
        any of the regular expressions, with the prefix string
        prepended to the key values of the dictionary.

        Parameters:
        - prefix (str): The prefix string to prepend to the key values.
        - regex_list (list of str): The list of regular expression patterns
            to match keys.
        - properties (dict): The input properties.

        Returns:
        - dict: A new dictionary containing filtered items with modified
                key values.
        """
        filtered_dict = {}

        # Compile the regular expression patterns
        compiled_regexes = [re.compile(regex) for regex in regex_list]

        # Iterate over the items in the input properties
        for key, value in properties.items():
            # Check if the key matches any of the regular expression patterns
            for pattern in compiled_regexes:
                if pattern.match(key):
                    # Prepend the prefix to the key value and add it to
                    # the new dictionary
                    if prefix:
                        filtered_dict[f"{prefix}.{key}"] = value
                    else:
                        filtered_dict[key] = value

                    self.active_prefixes.add(prefix)
                    break

        return filtered_dict

    def placeholder(self, property: SchemaObjectProperty, param: str) -> str:
        if self.engine == "oracle":
            if property.column_type == "date":
                return f"TO_DATE(:{param}, 'YYYY-MM-DD')"
            elif property.column_type == "datetime":
                return f"TO_TIMESTAMP(:{param}, 'YYYY-MM-DD\"T\"HH24:MI:SS.FF')"
            elif property.column_type == "time":
                return f"TO_TIME(:{param}, 'HH24:MI:SS.FF')"
            return f":{param}"
        return f"%({param})s"

    def concurrency_generator(self, property: SchemaObjectProperty) -> str:
        log.debug(f"api_type: {property.api_type}")
        if property.api_type == "date-time":
            return "CURRENT_TIMESTAMP"
        elif property.api_type == "integer":
            return f"{property.column_name} + 1"
        elif property.api_type == "string":
            if self.engine == "oracle":
                return "SYS_GUID()"
            if self.engine == "mysql":
                return "UUID()"
            return "gen_random_uuid()"
        raise ApplicationException(
            500, "Concurrency control property is unrecognized type"
        )

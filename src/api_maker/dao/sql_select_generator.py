from api_maker.dao.sql_generator import SQLGenerator
from api_maker.operation import Operation
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.utils.model_factory import SchemaObject

log = logger(__name__)


class SQLSelectGenerator(SQLGenerator):
    def __init__(
        self, operation: Operation, schema_object: SchemaObject, engine:str
    ) -> None:
        super().__init__(operation, schema_object, engine)

    @property
    def sql(self) -> str:
        return (
            "SELECT "
            + self.select_list
            + " FROM "
            + self.table_expression
            + self.search_condition
        )

    @property
    def select_list(self) -> str:
        if self.operation.metadata_params.get("_count", False):
            return "count(*)"
        return super().select_list

    @property
    def search_condition(self) -> str:
        self.search_placeholders = {}
        conditions = []

        for name, value in self.operation.query_params.items():
            parts = name.split(".")

            try:
                if len(parts) > 1:
                    relation = self.schema_object.relations[parts[0]]
                    if relation.type == "array":
                        raise ApplicationException(
                            400,
                            (
                                "Queries using properties in "
                                + "arrays is not supported. "
                                + "schema object: "
                                + self.schema_object.entity
                                + ", property: "
                                + name
                            ),
                        )
                    property = relation.child_schema_object.properties[
                        parts[1]
                    ]
                    prefix = self.prefix_map[parts[0]]
                else:
                    property = self.schema_object.properties[parts[0]]
                    prefix = self.prefix_map["$default$"]
            except KeyError:
                raise ApplicationException(
                    500,
                    (
                        "Invalid query parameter, property not found. "
                        + "schema object: "
                        + self.schema_object.entity
                        + ", property: "
                        + name
                    ),
                )

            assignment, holders = self.search_value_assignment(
                property, value, prefix if not self.single_table else None
            )
            conditions.append(assignment)
            self.search_placeholders.update(holders)

        return (
            f" WHERE {' AND '.join(conditions)}" if len(conditions) > 0 else ""
        )

    @property
    def table_expression(self) -> str:
        if self.single_table:
            return self.schema_object.table_name

        joins = []
        parent_prefix = self.prefix_map["$default$"]
        for name, relation in self.schema_object.relations.items():
            child_prefix = self.prefix_map[relation.name]
            if relation.type == "object":
                joins.append(
                    "INNER JOIN "
                    + relation.child_schema_object.table_name
                    + " AS "
                    + child_prefix
                    + " ON "
                    + parent_prefix
                    + "."
                    + relation.parent_property.column_name
                    + " = "
                    + child_prefix
                    + "."
                    + relation.child_property.column_name
                )

        return (
            self.schema_object.table_name
            + " AS "
            + self.prefix_map["$default$"]
            + f" {' '.join(joins)}"
            if len(joins) > 0
            else ""
        )

    def selection_result_map(self) -> dict:
        if self.single_table:
            return super().selection_result_map()

        filter_str = self.operation.metadata_params.get("_properties", ".*")
        self.__select_list_map = {}

        for relation, reg_exs in self.get_regex_map(filter_str).items():
            # Extract the schema object for the current entity
            relation_property = self.schema_object.relations.get(relation)

            if relation_property:
                if relation_property.type == "array":
                    continue

                # Use a default value if relation_property is None
                schema_object = relation_property.child_schema_object
            else:
                schema_object = self.schema_object

            # Filter and prefix keys for the current entity
            # and regular expressions
            filtered_keys = self.filter_and_prefix_keys(
                reg_exs, schema_object.properties, self.prefix_map[relation]
            )

            # Extend the result map with the filtered keys
            self.__select_list_map.update(filtered_keys)

        return self.__select_list_map

    def get_regex_map(self, filter_str: str) -> dict[str, list]:
        result = {}

        for filter in filter_str.split():
            parts = filter.split(":")
            entity = parts[0] if len(parts) > 1 else "$default$"
            expression = parts[-1]

            # Check if entity already exists in result, if not, initialize
            # it with an empty list
            if entity not in result:
                result[entity] = []

            # Append the expression to the list of expressions for the entity
            result[entity].append(expression)

        return result

    def marshal_record(self, record) -> dict:
        object_set = {}
        for name, value in record.items():
            property = self.selection_results[name]
            parts = name.split(".")
            component = (
                parts[0] if len(parts) > 1 else self.prefix_map["$default$"]
            )
            object = object_set.get(component, {})
            if not object:
                object_set[component] = object
            object[property.name] = property.convert_to_api_value(value)

        result = object_set[self.prefix_map["$default$"]]
        for name, prefix in self.prefix_map.items():
            if name != "$default$" and prefix in object_set:
                result[name] = object_set[prefix]

        return result

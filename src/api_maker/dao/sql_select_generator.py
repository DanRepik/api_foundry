from api_maker.dao.sql_generator import SQLGenerator
from api_maker.operation import Operation
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.utils.model_factory import SchemaObject, SchemaObjectProperty

log = logger(__name__)


class SQLSelectGenerator(SQLGenerator):
    def __init__(
        self, operation: Operation, schema_object: SchemaObject, engine: str
    ) -> None:
        super().__init__(operation, schema_object, engine)

    @property
    def sql(self) -> str:
        # order is important here table_expression must be last
        search_condition = self.search_condition
        order_by_expression = self.order_by_expression
        select_list = self.select_list
        table_expression = self.table_expression

        return (
            f"SELECT {select_list}"
            + f"FROM {table_expression}"
            + search_condition
            + order_by_expression
            + self.limit_expression
            + self.offset_expression
        )

    @property
    def select_list(self) -> str:
        if self.operation.metadata_params.get("count", False):
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
                    if parts[0] not in self.schema_object.relations:
                        raise ApplicationException(
                            400,
                            "Invalid selection property "
                            + self.schema_object.entity
                            + " does not have a property "
                            + parts[0],
                        )
                    relation = self.schema_object.relations[parts[0]]
                    if parts[1] not in relation.child_schema_object.properties:
                        raise ApplicationException(
                            400,
                            "Property not found, "
                            + relation.child_schema_object.entity
                            + " does not have property "
                            + parts[1],
                        )
                    property = relation.child_schema_object.properties[parts[1]]
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

        return f" WHERE {' AND '.join(conditions)}" if len(conditions) > 0 else ""

    @property
    def table_expression(self) -> str:
        #        if self.single_table:
        #            return self.schema_object.table_name

        joins = []
        parent_prefix = self.prefix_map["$default$"]
        log.info(f"active_prefixes: {self.active_prefixes}")
        for name, relation in self.schema_object.relations.items():
            child_prefix = self.prefix_map[relation.name]
            if child_prefix in self.active_prefixes:
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
            + (f" {' '.join(joins)}" if len(joins) > 0 else "")
        )

    def selection_result_map(self) -> dict:
        if "count" in self.operation.metadata_params:
            self.__selection_result_map = {
                "count": SchemaObjectProperty(
                    self.operation.entity, "count", {"type": "int"}
                )
            }
            return self.__selection_result_map

        filter_str = self.operation.metadata_params.get("properties", ".*")
        self.__selection_result_map = {}

        for relation, reg_exs in self.get_regex_map(filter_str).items():
            log.info(f"xx relation: {relation}, reg_exs: {reg_exs}")
            # Extract the schema object for the current entity
            relation_property = self.schema_object.relations.get(relation)

            if relation_property:
                if relation_property.type == "array":
                    continue

                # Use a default value if relation_property is None
                schema_object = relation_property.child_schema_object
            else:
                schema_object = self.schema_object

            if relation not in self.prefix_map:
                raise ApplicationException(
                    400,
                    "Bad object association: "
                    + schema_object.entity
                    + " does not have a "
                    + relation
                    + " property",
                )

            # Filter and prefix keys for the current entity
            # and regular expressions
            filtered_keys = self.filter_and_prefix_keys(
                reg_exs, schema_object.properties, self.prefix_map[relation]
            )

            # Extend the result map with the filtered keys
            self.__selection_result_map.update(filtered_keys)

        log.debug(f"xx select_list_map: {self.__selection_result_map}")
        return self.__selection_result_map

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
            component = parts[0] if len(parts) > 1 else self.prefix_map["$default$"]
            object = object_set.get(component, {})
            if not object:
                object_set[component] = object
            object[property.name] = property.convert_to_api_value(value)

        result = object_set[self.prefix_map["$default$"]]
        for name, prefix in self.prefix_map.items():
            if name != "$default$" and prefix in object_set:
                result[name] = object_set[prefix]

        return result

    @property
    def order_by_expression(self) -> str:
        fields_str = self.operation.metadata_params.get("sort", None)
        if not fields_str:
            return ""

        # determine the columns requested
        fields = fields_str.replace(",", " ").split()
        log.debug(f"fields: {fields}")

        order_set = []
        use_prefixes = False
        for field in fields:
            # handle order
            field_parts = field.split(":")
            field_name = field_parts[0]

            order = "asc" if len(field_parts) == 1 else field_parts[1]
            if order != "desc" and order != "asc":
                raise ApplicationException(400, f"unrecognized sorting order: {field}")

            # handle entity prefix
            field_parts = field_name.split(".")
            log.info(f"xx field_parts: {field_parts}")
            if len(field_parts) == 1:
                prefix = self.prefix_map["$default$"]
                property = self.schema_object.properties.get(field_parts[0])
                if not property:
                    raise ApplicationException(
                        400,
                        f"Invalid order by property, schema object: {self.schema_object.entity} does not have a property: {field_parts[0]}",  # noqa E501
                    )
                column = property.column_name
            else:
                # Extract the schema object for the current entity
                relation_property = self.schema_object.relations.get(field_parts[0])
                if not relation_property:
                    raise ApplicationException(
                        400,
                        f"Invalid order by property, schema object: {self.schema_object.entity} does not have a property: {field_parts[0]}",  # noqa E501
                    )

                log.info(f"relation_property: {relation_property}")
                if relation_property:
                    if relation_property.type == "array":
                        raise ApplicationException(
                            400,
                            f"Invalid order by array property is not supported, schema object: {self.schema_object.entity} property: {field_parts[0]}",  # noqa E501
                        )

                    # Use a default value if relation_property is None
                    schema_object = relation_property.child_schema_object
                else:
                    schema_object = self.schema_object

                prefix = self.prefix_map[field_parts[0]]
                property = schema_object.properties.get(field_parts[1])
                if not property:
                    raise ApplicationException(
                        400,
                        f"Invalid order by property, schema object: {schema_object.entity} does not have a property: {field_parts[1]}",  # noqa E501
                    )
                column = property.column_name
                self.active_prefixes.add(prefix)
                use_prefixes = True

            order_set.append((prefix, column, order))

        if len(order_set) == 0:
            return ""
        order_parts = []
        for prefix, column, order in order_set:
            if use_prefixes:
                order_parts.append(f"{prefix}.{column} {order}")
            else:
                order_parts.append(f"{column} {order}")
        return " ORDER BY " + ", ".join(order_parts)

    @property
    def limit_expression(self) -> str:
        limit_str = self.operation.metadata_params.get("limit", None)
        if not limit_str:
            return ""

        if isinstance(limit_str, str) and not limit_str.isdigit():
            raise ApplicationException(
                400, f"Limit is not an valid integer {limit_str}"
            )

        return f" LIMIT {limit_str}"

    @property
    def offset_expression(self) -> str:
        offset_str = self.operation.metadata_params.get("offset", None)
        log.debug(f"xx offset: {offset_str}")
        if not offset_str:
            return ""

        log.debug(f"xxx offset: {offset_str}")
        if isinstance(offset_str, str) and not offset_str.isdigit():
            raise ApplicationException(
                400, f"Offset is not an valid integer {offset_str}"
            )

        return f" offset {offset_str}"

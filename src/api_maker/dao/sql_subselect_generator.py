from api_maker.dao.sql_generator import SQLGenerator
from api_maker.dao.sql_select_generator import SQLSelectGenerator
from api_maker.operation import Operation
from api_maker.utils.logger import logger
from api_maker.utils.model_factory import SchemaObject, SchemaObjectRelation

log = logger(__name__)


class SQLSubselectGenerator(SQLSelectGenerator):

    def __init__(
        self,
        operation: Operation,
        relation: SchemaObjectRelation,
        parent_generator: SQLGenerator,
    ) -> None:
        super().__init__(operation, relation.child_schema_object)
        self.relation = relation
        self.parent_generator = parent_generator

    def selection_result_map(self) -> dict:
        filter_str = self.operation.metadata_params.get("_properties", "")
        log.info(f"Filter string: {filter_str}")
        result = {self.relation.child_property.name: self.relation.child_property}

        log.info(f"Building map; {self.get_regex_map(filter_str)}")
        for relation_name, reg_exs in self.get_regex_map(filter_str).items():
            log.info(f"relation: {relation_name}, reg_exs: {reg_exs}")

            if relation_name != self.relation.name:
                continue

            schema_object = self.relation.child_schema_object

            log.info(f"schema_object: {schema_object.entity}")

            # Filter and prefix keys for the current entity and regular expressions
            filtered_keys = self.filter_and_prefix_keys(
                reg_exs, schema_object.properties
            )
            log.info(f"filtered_keys: {filtered_keys}")

            # Extend the result map with the filtered keys
            result.update(filtered_keys)

        log.info(f"result: {result}")
        return result

    @property
    def placeholders(self) -> dict:
        return self.search_placeholders

    @property
    def sql(self) -> str:
        sql = (
            f"SELECT {self.select_list} "
            + f"FROM {self.relation.child_schema_object.table_name} "
            + f"WHERE {self.relation.child_property.column_name} "
            + f"IN ( SELECT {self.relation.parent_property.column_name} "
            + f"FROM {self.parent_generator.table_expression}{self.parent_generator.search_condition} "
            #            + f"{order_by} {limit} {offset})"
            + ")"
        )
        log.debug(f"subselect sql: {sql}")
        self.search_placeholders = self.parent_generator.search_placeholders
        #        self._execute_sql(args["cursor"], sql, query_parameters)
        return sql

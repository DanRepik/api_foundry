from api_maker.dao.sql_generator import SQLGenerator
from api_maker.operation import Operation
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.utils.model_factory import SchemaObject

log = logger(__name__)


class SQLUpdateGenerator(SQLGenerator):
    def __init__(self, operation: Operation, schema_object: SchemaObject) -> None:
        super().__init__(operation, schema_object)

    @property
    def sql(self) -> str:
        concurrency_property = self.schema_object.concurrency_property
        if not concurrency_property:
            return f"UPDATE {self.table_expression}{self.update_values}{self.search_condition} RETURNING {self.select_list}"

        log.info(f"concurrency_property: {vars(concurrency_property)}")
        if not self.operation.query_params.get(concurrency_property.name):
            raise ApplicationException(
                400,
                "For updating concurrency managed schema objects the current version must be supplied as a query parameter." + 
                f"  schema_object: {self.schema_object.entity}, property: {concurrency_property.name}",
            )
        if self.operation.store_params.get(concurrency_property.name):
            raise ApplicationException(
                400,
                "For updating concurrency managed schema objects the current version may not be supplied as a storage parameter." + 
                f"  schema_object: {self.schema_object.entity}, property: {concurrency_property.name}",
            )

        return f"UPDATE {self.table_expression}{self.update_values}, {concurrency_property.column_name} = {self.concurrency_generator(concurrency_property)} {self.search_condition} RETURNING {self.select_list}"

    @property
    def update_values(self) -> str:
        log.info(f"update_values store_params: {self.operation.store_params}")

        self.store_placeholders = {}
        columns = []

        for name, value in self.operation.store_params.items():
            try:
                property = self.schema_object.properties[name]
            except KeyError:
                raise ApplicationException(
                    400, f"Search condition column not found {name}"
                )

            log.info(f"name: {name}, value: {value}")

            placeholder = property.name
            column_name = property.column_name

            columns.append(f"{column_name} = {self.placeholder(property, placeholder)}")
            self.store_placeholders[placeholder] = property.convert_to_db_value(value)

        return f" SET {', '.join(columns)}"

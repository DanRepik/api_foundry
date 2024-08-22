from api_foundry.dao.sql_query_handler import SQLSchemaQueryHandler
from api_foundry.operation import Operation
from api_foundry.utils.app_exception import ApplicationException
from api_foundry.utils.model_factory import SchemaObject


class SQLUpdateSchemaQueryHandler(SQLSchemaQueryHandler):
    def __init__(
        self, operation: Operation, schema_object: SchemaObject, engine: str
    ) -> None:
        super().__init__(operation, schema_object, engine)

    @property
    def sql(self) -> str:
        concurrency_property = self.schema_object.concurrency_property
        if not concurrency_property:
            return (
                f"UPDATE {self.table_expression}{self.update_values}"
                + f"{self.search_condition} RETURNING {self.select_list}"
            )

        if not self.operation.query_params.get(concurrency_property.name):
            raise ApplicationException(
                400,
                "Missing required concurrency management property.  "
                + f"schema_object: {self.schema_object.operation_id}, "
                + f"property: {concurrency_property.name}",
            )
        if self.operation.store_params.get(concurrency_property.name):
            raise ApplicationException(
                400,
                "For updating concurrency managed schema objects the current version "
                + " may not be supplied as a storage parameter.  "
                + f"schema_object: {self.schema_object.operation_id}, "
                + f"property: {concurrency_property.name}",
            )

        return f"UPDATE {self.table_expression}{self.update_values}, {concurrency_property.column_name} = {self.concurrency_generator(concurrency_property)} {self.search_condition} RETURNING {self.select_list}"  # noqa E501

    @property
    def update_values(self) -> str:
        self.store_placeholders = {}
        columns = []

        for name, value in self.operation.store_params.items():
            try:
                property = self.schema_object.properties[name]
            except KeyError:
                raise ApplicationException(
                    400, f"Search condition column not found {name}"
                )

            placeholder = property.name
            column_name = property.column_name

            columns.append(f"{column_name} = {self.placeholder(property, placeholder)}")
            self.store_placeholders[placeholder] = property.convert_to_db_value(value)

        return f" SET {', '.join(columns)}"

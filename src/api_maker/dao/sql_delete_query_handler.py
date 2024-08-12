from api_maker.dao.sql_query_handler import SQLSchemaQueryHandler
from api_maker.operation import Operation
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.model_factory import SchemaObject


class SQLDeleteSchemaQueryHandler(SQLSchemaQueryHandler):
    def __init__(
        self, operation: Operation, schema_object: SchemaObject, engine: str
    ) -> None:
        super().__init__(operation, schema_object, engine)

    @property
    def sql(self) -> str:
        concurrency_property = self.schema_object.concurrency_property
        if concurrency_property and not self.operation.query_params.get(
            concurrency_property.name
        ):
            raise ApplicationException(
                400,
                "Missing required concurrency management property."
                + f"  schema_object: {self.schema_object.operation_id}, property: {concurrency_property.name}",  # noqa E501
            )

        return f"DELETE FROM {self.table_expression}{self.search_condition} RETURNING {self.select_list}"  # noqa E501

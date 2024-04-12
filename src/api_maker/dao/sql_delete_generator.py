from api_maker.dao.sql_generator import SQLGenerator
from api_maker.operation import Operation
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.utils.model_factory import SchemaObject

log = logger(__name__)


class SQLDeleteGenerator(SQLGenerator):
    def __init__(self, operation: Operation, schema_object: SchemaObject) -> None:
        super().__init__(operation, schema_object)

    @property
    def sql(self) -> str:
        return f"DELETE FROM {self.table_expression}{self.search_condition} RETURNING {self.select_list}"

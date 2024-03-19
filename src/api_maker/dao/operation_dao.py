from api_maker.utils.app_exception import ApplicationException
from api_maker.dao.dao import DAO
from api_maker.connectors.connector import Connector, Cursor
from api_maker.operation import Operation
from api_maker.utils.model_factory import ModelFactory
from api_maker.dao.sql_generator import SQLGenerator


class OperationDAO(DAO):
    
    def __init__(self, operation: Operation) -> None:
        super().__init__()
        self.operation = operation


    def execute(self, cursor: Cursor) -> list[dict]:
        if self.operation.action in ["read", "create", "update", "delete"]:
            sql_generator = SQLGenerator(
                self.operation, ModelFactory.get_schema_object(operation.entity)
            )
            records = cursor.execute(sql_generator.sql, sql_generator.params)

        else:
            raise ApplicationException(500, "Invalid operaton action")

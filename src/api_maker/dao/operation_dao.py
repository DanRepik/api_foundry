from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.dao.dao import DAO
from api_maker.connectors.connection import Cursor
from api_maker.operation import Operation
from api_maker.utils.model_factory import ModelFactory
from api_maker.dao.sql_generator import SQLGenerator

log = logger(__name__)

class OperationDAO(DAO):
    
    def __init__(self, operation: Operation) -> None:
        super().__init__()
        self.operation = operation


    def execute(self, cursor: Cursor) -> list[dict]:
        if self.operation.action in ["read", "create", "update", "delete"]:
            sql_generator = SQLGenerator(
                self.operation, ModelFactory.get_schema_object(self.operation.entity)
            )
            result = []
            record_set = cursor.execute(sql_generator.sql, sql_generator.search_placeholders, sql_generator.result_fields)
            for record in record_set:
                object = sql_generator.marshal_record(record)
                log.info(f"object: {object}")
                result.append(object)
            return result

        raise ApplicationException(500, "Invalid operaton action")


import traceback

from api_maker.utils.logger import logger
from api_maker.utils.model_factory import SchemaObject
from api_maker.operation import Operation
from api_maker.services.service import ServiceAdapter
from api_maker.connectors.connection_factory import connection_factory
from api_maker.connectors.connection import Connection
from api_maker.dao.operation_dao import OperationDAO
from api_maker.utils.model_factory import ModelFactory

log = logger(__name__)


class TransactionalService(ServiceAdapter):
    def execute(self, operation: Operation):
        api_object = ModelFactory.get_api_object(operation.entity, operation.action)
        connection = connection_factory.get_connection(api_object.database)

        try:
            result = None
            cursor = connection.cursor()
            try:
                result = OperationDAO(operation, connection.engine()).execute(cursor)
            finally:
                cursor.close()
            if operation.action != "read":
                connection.commit()
            return result
        except Exception as error:
            log.error(f"transaction exception: {error}")
            log.error(f"traceback: {traceback.format_exc()}")
            raise error
        finally:
            connection.close()

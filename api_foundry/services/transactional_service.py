import traceback

from api_foundry.utils.logger import logger
from api_foundry.operation import Operation
from api_foundry.services.service import ServiceAdapter
from api_foundry.connectors.connection_factory import connection_factory
from api_foundry.dao.operation_dao import OperationDAO
from api_foundry.utils.model_factory import ModelFactory

log = logger(__name__)


class TransactionalService(ServiceAdapter):
    def execute(self, operation: Operation):
        api_object = ModelFactory.get_api_object(
            operation.operation_id, operation.action
        )
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

import traceback

from api_maker.utils.logger import logger
from api_maker.utils.model_factory import SchemaObject
from api_maker.operation import Operation
from api_maker.services.service import ServiceAdapter
from api_maker.connectors.connector_factory import connector_factory
from api_maker.connectors.connector import Connector
from api_maker.dao.operation_dao import OperationDAO
from api_maker.utils.model_factory import ModelFactory

log = logger(__name__)

class TransactionalService(ServiceAdapter):

  def execute(self, operation: Operation):
    schema_object = ModelFactory.get_schema_object(operation.entity)
    connector = connector_factory(engine=schema_object.engine, database=schema_object.database)
    try: 
        cursor = connector.cursor()
        try:
            return OperationDAO(operation).execute()
        finally:
           cursor.close()
        if operation.action != 'read':
            connector.commit()
    except Exception as error:
        log.error(f"transaction exception: {error}")
        log.error(f"traceback: {traceback.format_exc()}")
        raise error
    finally:
      connector.close()


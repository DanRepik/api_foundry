from api_maker.utils.logger import logger
from api_maker.operation import Operation
from api_maker.services.service import ServiceAdapter
from api_maker.connectors.connector_factory import connector_factory
from api_maker.connectors.connector import Connector
from api_maker.utils.model_factory import ModelFactory

log = logger(__name__)

class TransactionalService(ServiceAdapter):

  def execute(self, operation: Operation):
    model = ModelFactory.get_schema_object(operation.entity)
    connector = connector_factory(engine=model.engine, database=model.database)
    if operation.action == 'read':
        self.query(connector, operation)
    else:
         self.mutate(connector, operation)

  def mutate(self, connector: Connector, operation, **args) -> list[dict]:
    """
    Execute a mutation operation on the database.
    """
    try:
        result = operation(connection=connection, **args)
        connector.commit()

    except Exception as error:
        log.error(f"transaction exception: {error}")
        log.error(f"traceback: {traceback.format_exc()}")
        raise error

    finally:
        connection.close()

    return result

  def query(self, connector: Connector, operation, **args) -> list[dict]:
      pass


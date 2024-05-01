from api_maker.dao.sql_delete_generator import SQLDeleteGenerator
from api_maker.dao.sql_insert_generator import SQLInsertGenerator
from api_maker.dao.sql_select_generator import SQLSelectGenerator
from api_maker.dao.sql_subselect_generator import SQLSubselectGenerator
from api_maker.dao.sql_update_generator import SQLUpdateGenerator
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.dao.dao import DAO
from api_maker.connectors.connection import Cursor
from api_maker.operation import Operation
from api_maker.utils.model_factory import ModelFactory
from api_maker.dao.sql_generator import SQLGenerator

log = logger(__name__)

class OperationDAO(DAO):
    """
    A class to handle database operations based on the provided Operation object.

    Attributes:
        operation (Operation): The operation to perform.
    """
    
    def __init__(self, operation: Operation) -> None:
        """
        Initialize the OperationDAO with the provided Operation object.

        Args:
            operation (Operation): The operation to perform.
        """
        super().__init__()
        self.operation = operation
        self.schema_object = ModelFactory.get_schema_object(self.operation.entity)
        self.sql_generator = self.__sql_generator()

    def __sql_generator(self) -> SQLGenerator:
        if self.operation.action == "read":
            return SQLSelectGenerator(self.operation, self.schema_object)
        elif self.operation.action == "create":
            return SQLInsertGenerator(self.operation, self.schema_object)
        elif self.operation.action == "update":
            return SQLUpdateGenerator(self.operation, self.schema_object)
        elif self.operation.action == "delete":
            return SQLDeleteGenerator(self.operation, self.schema_object)
        
        raise ApplicationException(400, f"Invalid operation action: {self.operation.action}")
    
    def execute(self, cursor: Cursor) -> list[dict]:
        """
        Execute the database operation based on the provided cursor.

        Args:
            cursor (Cursor): The database cursor.

        Returns:
            list[dict]: A list of dictionaries containing the results of the operation.
        """

        result = self.__fetch_record_set(self.sql_generator, cursor)

        if self.operation.action == "read":
            self.__fetch_many(result, cursor)

        return result


    def __fetch_many(self, parent_set: list[dict], cursor: Cursor):
        for name, relation in self.schema_object.relations.items():
            log.info(f"checking relation: {name}, relation: {vars(relation)}")
            if relation.cardinality != "1:m":
                continue

            subselect_generator = SQLSubselectGenerator(self.operation, relation, self.sql_generator)
            log.info(f"subselect_sql: {subselect_generator.sql}")
            child_set = self.__fetch_record_set(subselect_generator, cursor)

            for parent in parent_set:
                parent[name] = []

            log.info(f"child_set: {child_set}")

            if len(child_set) == 0:
                continue

            parents = {}
            log.info(f"parent_property: {vars(relation.parent_property)}")
            for parent in parent_set:
                parents[parent[relation.parent_property.name]] = parent

            log.info(f"parents: {parents}")
            for child in child_set:
                log.info(f"child {child}")
                parent_id = child[relation.child_property.name]
                parent = parents.get(parent_id)
                if parent:
                    parent[name].append(child)

    def __fetch_record_set(self, generator: SQLGenerator, cursor: Cursor) -> list[dict]:
        result = []
        record_set = cursor.execute(generator.sql, generator.placeholders, generator.select_list_columns)
        for record in record_set:
            object = generator.marshal_record(record)
            log.info(f"object: {object}")
            result.append(object)

        return result


from api_maker.dao.sql_generator import SQLGenerator
from api_maker.operation import Operation
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.utils.model_factory import SchemaObject

log = logger(__name__)


class SQLInsertGenerator(SQLGenerator):
    def __init__(self, operation: Operation, schema_object: SchemaObject) -> None:
        super().__init__(operation, schema_object)
        self.key_property = schema_object.primary_key
        if self.key_property is not None:
            if self.key_property.type == "auto":
                if operation.store_params.get(self.key_property.column_name):
                    raise ApplicationException(400, f"Primary key values cannot be inserted when key type is auto. schema_object: {schema_object.entity}")
            elif self.key_property.type == "required": 
                if not operation.store_params.get(self.key_property.column_name):
                    raise ApplicationException(400, f"Primary key values must be provided when key type is required. schema_object: {schema_object.entity}")


    @property
    def sql(self) -> str:
        return f"INSERT INTO {self.table_expression}{self.insert_values} RETURNING {self.select_list}"

    @property
    def insert_values(self) -> str:
        log.info(f"insert_values store_params: {self.operation.store_params}")

        self.store_placeholders = {}
        placeholders = []
        columns = []

        for name, value in self.operation.store_params.items():
            parts = name.split(".")
            log.info(f"parts: {parts}")

            try:
                if len(parts) > 1:
                    raise ApplicationException(
                        400, f"Properties can not be set on related objects {name}"
                    )

                property = self.schema_object.properties[parts[0]]
            except KeyError:
                raise ApplicationException(
                    400, f"Invalid property: {name}"
                )

            log.info(f"name: {name}, value: {value}")
            columns.append(property.column_name)
            placeholders.append(property.name)
            self.store_placeholders[property.name] = property.convert_to_db_value(value)

        if self.key_property:
            if self.key_property.type == "sequence":
                columns.append(self.key_property.column_name)
                placeholders.append(f"nextval('{self.key_property.sequence_name}')")


        return f" ( {', '.join(columns)} ) VALUES ( {', '.join(placeholders)})"


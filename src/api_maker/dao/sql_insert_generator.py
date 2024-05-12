from api_maker.dao.sql_generator import SQLGenerator
from api_maker.operation import Operation
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.utils.model_factory import SchemaObject

log = logger(__name__)


class SQLInsertGenerator(SQLGenerator):
    def __init__(
        self, operation: Operation, schema_object: SchemaObject
    ) -> None:
        super().__init__(operation, schema_object)
        self.key_property = schema_object.primary_key
        if self.key_property:
            if self.key_property.key_type == "auto":
                if operation.store_params.get(self.key_property.column_name):
                    raise ApplicationException(
                        400,
                        "Primary key values cannot be inserted when key type"
                        + f" is auto. schema_object: {schema_object.entity}",
                    )
            elif self.key_property.key_type == "required":
                if not operation.store_params.get(
                    self.key_property.column_name
                ):
                    raise ApplicationException(
                        400,
                        "Primary key values must be provided when key type is"
                        + f" required. schema_object: {schema_object.entity}",
                    )
        self.concurrency_property = schema_object.concurrency_property
        if self.concurrency_property and operation.store_params.get(
            self.concurrency_property.name
        ):
            raise ApplicationException(
                400,
                "Versioned properties can not be supplied a store parameters. "
                + f"schema_object: {schema_object.entity}, "
                + f"property: {self.concurrency_property.name}",
            )

    @property
    def sql(self) -> str:
        self.concurrency_property = self.schema_object.concurrency_property
        if not self.concurrency_property:
            return (
                f"INSERT INTO {self.table_expression}{self.insert_values} "
                + f"RETURNING {self.select_list}"
            )

        log.info(f"version_property: {vars(self.concurrency_property)}")
        if self.operation.store_params.get(self.concurrency_property.name):
            raise ApplicationException(
                400,
                "When inserting schema objects with a version property "
                + "the a version must not be supplied as a storage parameter."
                + f"  schema_object: {self.schema_object.entity}, "
                + f"property: {self.concurrency_property.name}",
            )
        return (
            f"INSERT INTO {self.table_expression}{self.insert_values}"
            + f" RETURNING {self.select_list}"
        )

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
                        400,
                        "Properties can not be set on associated objects "
                        + name,
                    )

                property = self.schema_object.properties[parts[0]]
            except KeyError:
                raise ApplicationException(400, f"Invalid property: {name}")

            log.info(f"name: {name}, value: {value}")
            columns.append(property.column_name)
            placeholders.append(self.placeholder(property, property.name))
            self.store_placeholders[
                property.name
            ] = property.convert_to_db_value(value)

        if self.key_property:
            if self.key_property.key_type == "sequence":
                columns.append(self.key_property.column_name)
                placeholders.append(
                    f"nextval('{self.key_property.sequence_name}')"
                )

        if self.concurrency_property:
            columns.append(self.concurrency_property.column_name)
            if self.concurrency_property.type == "integer":
                placeholders.append("1")
            else:
                placeholders.append(
                    self.concurrency_generator(self.concurrency_property)
                )

        return f" ( {', '.join(columns)} ) VALUES ( {', '.join(placeholders)})"

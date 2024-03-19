import os
from typing import Any
import yaml
from datetime import date, datetime, time

from api_maker.utils.logger import logger

log = logger(__name__)


class SchemaObjectRelation:
    def __init__(self, entity: str, name: str, properties: dict):
        assert entity is not None
        assert properties is not None
        assert name is not None
        self.entity = entity
        self.name = name
        self.cardinality = properties.get("x-am-cardinality", "1:1")
        self.parent_key = properties.get("x-am-parent-property")
        self.child_key = properties.get("x-am-child-property", None)
        log.debug(f"schema name: {properties['x-am-schema']}")
        self.schema_object = ModelFactory.get_schema_object(properties["x-am-schema"])


from datetime import datetime, date, time

class SchemaObjectProperty:
    def __init__(self, engine: str, entity: str, name: str, properties: dict):
        assert engine is not None
        assert entity is not None
        assert properties is not None
        assert name is not None
        self.engine = engine
        self.entity = entity
        self.name = name
        self.column_name = properties.get('x-am-column-name', name)
        self.type = properties.get("type", "string")
        self.format = properties.get("format")
        self.column_type = properties.get("x-am-column-type", self.type)
        if self.format in [ 'float', 'date', 'date-time', 'time']:
            self.column_type = self.format
        

    def convert_to_db_value(self, value: str):
        log.info(f"convert_to_db type: {self.column_type}, value:{value}, column_type: {self.column_type}")
        if value is None:
            return None

        conversion_mapping = {
            "string": lambda x: x,
            "number": float,
            "float": float,
            "integer": int,
            "boolean": lambda x: x.lower() == "true",
            "date": lambda x: datetime.strptime(x, "%Y-%m-%d").date() if x else None,
            "date-time": lambda x: datetime.fromisoformat(x) if x else None,
            "time": lambda x: datetime.strptime(x, "%H:%M:%S").time() if x else None,
            # Add more conversions for other formats as needed
        }

        conversion_func = conversion_mapping.get(self.column_type, lambda x: x) # type: ignore
        return conversion_func(value)



class SchemaObject:
    def __init__(self, entity: str, schema_object: dict):
        log.info(f"schema_object: {schema_object}")
        assert entity is not None
        assert schema_object is not None
        self.entity = entity
        self.__schema_object = schema_object
        engine = schema_object.get("x-am-engine", "").lower()
        assert(engine in ['postgres', 'oracle', 'mysql'])
        self.engine = engine

        self.properties = dict()
        self.relations = dict()
        for property_name, property in schema_object.get("properties", {}).items():
            type = property.get("x-am-column-type", property.get("type", "string"))
            log.debug(f"property_name: {property_name}, type: {type}")
            if type == "relation":
                self.relations[property_name] = SchemaObjectRelation(
                    self.entity, property_name, property
                )
            else:
                self.properties[property_name] = SchemaObjectProperty(
                    self.engine,
                    self.entity, property_name, property
                )

        log.info(f"relations: {self.relations}")

    def get_property(self, property_name: str) -> SchemaObjectProperty | None:
        return self.properties.get(property_name)

    def get_relation(self, property_name: str) -> SchemaObjectRelation | None:
        return self.relations.get(property_name)

    @property
    def table_name(self):
        return f"{self.__schema_object.get('x-am-database')}.{self.__schema_object.get('x-am-table', self.entity)}"


class ModelFactory:

    __document = None

    @classmethod
    def get_schema_object(cls, entity: str) -> SchemaObject:
        return SchemaObject(
            entity,
            cls.__get_document_spec()
            .get("components", {})
            .get("schemas", {})
            .get(entity.lower().replace("_", "-")),
        )

    @classmethod
    def get_operation(cls, entity: str, operation: str):
        return cls.__get_document_spec().get("paths", {}).get(entity, {}).get(operation)

    @classmethod
    def __get_document_spec(cls):
        if not cls.__document:
            with open(os.environ["API_SPEC"], "r") as yaml_file:
                cls.__document = yaml.safe_load(yaml_file)

            components = cls.__document.get("components", {})
            schemas = components.get("schemas", {})
            components["schemas"] = {
                key.lower().replace("_", "-"): value for key, value in schemas.items()
            }

        log.info(
            f"entities: {cls.__document.get('components', {}).get('schemas', {}).keys()}"
        )
        return cls.__document

import os
import yaml
from typing import Any, Dict, Optional
from datetime import datetime, date, time
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger

log = logger(__name__)


class SchemaObjectRelation:
    def __init__(self, entity: str, name: str, properties: Dict[str, Any]):
        assert all(arg is not None for arg in (entity, name, properties))
        self.entity = entity
        self.name = name
        self.cardinality = properties.get("x-am-cardinality", "1:1")
        assert self.cardinality in [
            "1:1",
            "1:m",
        ], f"Cardinality incorrect name: {self.name}, cardinality: {self.cardinality}"
        self.child_schema_object = ModelFactory.get_schema_object(
            properties["x-am-schema-object"]
        )
        self.parent = properties.get("x-am-parent-property", None)
        self.child = properties.get("x-am-child-property", None)

    @property
    def child_property(self):
        if self.child:
            return self.child_schema_object.get_property(self.child)
        else:
            return self.child_schema_object.primary_key

    @property
    def parent_property(self):
        parent_schema_object = ModelFactory.get_schema_object(self.entity)
        if self.parent:
            return parent_schema_object.get_property(self.parent)
        else:
            return parent_schema_object.primary_key


class SchemaObjectProperty:
    def __init__(self, engine: str, entity: str, name: str, properties: Dict[str, Any]):
        assert all(arg is not None for arg in (engine, entity, name, properties))
        self.engine = engine
        self.entity = entity
        self.name = name
        self.column_name = properties.get("x-am-column-name", name)
        self.type = properties.get("type", "string")
        self.api_type = properties.get("format", self.type)
        self.column_type = properties.get("x-am-column-type", self.api_type)
        self.is_primary_key = properties.get("x-am-primary-key", False)

        self.concurrency_control = properties.get("x-am-concurrency-control")
        if self.concurrency_control:
            self.concurrency_control = self.concurrency_control.lower()
            assert self.concurrency_control in [
                "uuid",
                "timestamp",
                "serial",
            ], f"Unrecognized version type, schema object: {self.entity}, property: {name}, version_type: {self.concurrency_control}"

    def convert_to_db_value(self, value: str) -> Optional[Any]:
        #        log.info(f"convert_to_db type: {self.type}, value:{value}, column_type: {self.column_type}")
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
        }
        conversion_func = conversion_mapping.get(self.column_type, lambda x: x)
        return conversion_func(value)

    def convert_to_api_value(self, value) -> Optional[Any]:
        #        log.info(f"self: {vars(self)}")
        #        log.info(f"convert_to_api type: {self.api_type}, value:{value}, type: {type(value)}, column_type: {self.column_type}")
        if value is None:
            return None
        conversion_mapping = {
            "string": lambda x: x,
            "number": float,
            "float": float,
            "integer": int,
            "boolean": str,
            "date": lambda x: x.date().isoformat() if x else None,
            "date-time": lambda x: x.isoformat() if x else None,
            "time": lambda x: x.time().isoformat() if x else None,
        }
        conversion_func = conversion_mapping.get(self.api_type, lambda x: x)
        return conversion_func(value)


class SchemaObjectKey(SchemaObjectProperty):
    def __init__(self, engine: str, entity: str, name: str, properties: Dict[str, Any]):
        super().__init__(engine, entity, name, properties)
        self.key_type = properties.get("x-am-primary-key", "auto")
        if self.key_type not in ["required", "auto", "sequence"]:
            raise ApplicationException(
                500,
                f"Invalid primary key type must be one of required, auto, sequence.  schema_object: {self.entity}, property: {self.name}, type: {self.type}",
            )

        self.sequence_name = properties.get("x-am-sequence-name") if self.key_type == "sequence" else None        
        if self.key_type == "sequence" and not self.sequence_name:
            raise ApplicationException(
                500,
                f"Sequence-based primary keys must have a sequence name. Schema object: {self.entity}, Property: {self.name}",
            )


class SchemaObject:
    def __init__(self, entity: str, schema_object: Dict[str, Any]):
        assert all(arg is not None for arg in (entity, schema_object))
        self.entity = entity
        self.__schema_object = schema_object
        self.engine = schema_object.get("x-am-engine", "").lower()
        assert self.engine in [
            "postgres",
            "oracle",
            "mysql",
        ], f"Unrecognized engine entity: {self.entity}, engine: {self.engine}"
        self.database = schema_object["x-am-database"].lower()
        self.properties = {}
        self.relations = {}
        self.primary_key = None
        self.concurrency_property = None
        for property_name, prop in schema_object.get("properties", {}).items():
            assert (
                prop != None
            ), f"Property is none entity: {self.entity}, property: {property_name}"
            if prop.get("x-am-schema-object", None):
                self.relations[property_name] = SchemaObjectRelation(
                    self.entity, property_name, prop
                )
            else:
                object_property = SchemaObjectProperty(
                    self.engine, self.entity, property_name, prop
                )
                self.properties[property_name] = object_property
                if object_property.is_primary_key:
                    self.primary_key = SchemaObjectKey(
                        self.engine, self.entity, property_name, prop
                    )
                elif object_property.concurrency_control:
                    self.concurrency_property = object_property

    #        log.info(f"relations: {self.relations}")

    @property
    def table_name(self) -> str:
        return f"{self.__schema_object.get('x-am-database')}.{self.__schema_object.get('x-am-table', self.entity)}"

    def get_property(self, property_name: str) -> Optional[SchemaObjectProperty]:
        return self.properties.get(property_name)

    def get_relation(self, property_name: str) -> SchemaObjectRelation:
        try:
            return self.relations[property_name]
        except:
            raise ApplicationException(
                500, "Unknown relation {property_name}, check api spec.subselect sql:"
            )


class ModelFactory:
    @classmethod
    def load_spec(cls, api_spec_path: str = os.environ["API_SPEC"]):
        cls.__schemas = dict()
        if api_spec_path:
            with open(api_spec_path, "r") as yaml_file:
                cls.__document = yaml.safe_load(yaml_file)

            schemas = cls.__document.get("components", {}).get("schemas", {})
            for name, schema in schemas.items():
                cls.__schemas[name.lower().replace("_", "-")] = schema

        log.info(f"schemas: {cls.__schemas.keys()}")

    @classmethod
    def get_schema_object(cls, name: str) -> SchemaObject:
        return SchemaObject(name, cls.__schemas[name.lower().replace("_", "-")])
    


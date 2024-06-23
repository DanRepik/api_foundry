import yaml
from typing import Any, Dict, Optional
from datetime import datetime
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger

log = logger(__name__)


class OpenAPIElement:
    def __init__(self, properties: dict):
        self.properties = properties
        self.title = self.properties.get("title", None)
        self.description = self.properties.get("description", None)
        self.required = self.properties.get("required", None)
        self.type = self.properties.get("type", None)

    def resolve_reference(self, reference: Optional[str]) -> dict:
        """
        Resolves the reference in the OpenAPI specification and returns the referenced element.

        Args:
            openapi_spec (dict): The OpenAPI specification document as a Python dictionary.
            reference (str): The reference string to resolve (e.g., '#/components/schemas/SchemaA').

        Returns:
            object: The referenced element from the OpenAPI specification.
        """
        if not reference:
            return {}

        try:
            current_element = ModelFactory.spec
            if not current_element:
                return {}

            # Iterate over each component to traverse the specification
            for component in reference.lower().split("/"):
                if component == "#":
                    continue
                elif component in current_element:
                    # Move to the next element
                    current_element = current_element[component]
                else:
                    raise ApplicationException(500, f"Reference not found: {reference}")

            return current_element
        except Exception as e:
            log.error(f"exception: {e}")

        return {}


class SchemaObjectAssociation(OpenAPIElement):
    def __init__(self, entity: str, name: str, properties: Dict[str, Any]):
        super().__init__(properties)
        assert all(arg is not None for arg in (entity, name, properties))
        self.entity = entity
        self.name = name

        self.child_schema_object = ModelFactory.get_schema_object(
            properties["$ref"].split("/")[-1]
        )
        self.parent = properties.get("x-am-parent-property", None)
        self.child = properties.get("x-am-child-property", None)

    @property
    def child_property(self) -> Any:
        if self.child:
            return self.child_schema_object.get_property(self.child)
        return self.child_schema_object.primary_key

    @property
    def parent_property(self) -> Any:
        parent_schema_object = ModelFactory.get_schema_object(self.entity)
        if self.parent:
            return parent_schema_object.get_property(self.parent)
        return parent_schema_object.primary_key


class SchemaObjectProperty(OpenAPIElement):
    def __init__(self, entity: str, name: str, properties: Dict[str, Any]):
        super().__init__(properties)
        self.entity = entity
        self.name = name
        self.column_name = properties.get("x-am-column-name", name)
        self.type = properties.get("type", "string")
        self.api_type = properties.get("format", self.type)
        self.column_type = properties.get("x-am-column-type", self.api_type)
        self.is_primary_key = properties.get("x-am-primary-key", False)
        self.min_length = properties.get("minLength", None)
        self.max_length = properties.get("maxLength", None)
        self.pattern = properties.get("pattern", None)

        self.concurrency_control = properties.get("x-am-concurrency-control")
        if self.concurrency_control:
            self.concurrency_control = self.concurrency_control.lower()
            assert self.concurrency_control in [
                "uuid",
                "timestamp",
                "serial",
            ], (
                "Unrecognized version type, schema object: {self.entity}, "
                + f"property: {name}, version_type: {self.concurrency_control}"
            )

    def convert_to_db_value(self, value: str) -> Optional[Any]:
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
    def __init__(self, entity: str, name: str, properties: Dict[str, Any]):
        super().__init__(entity, name, properties)
        self.key_type = properties.get("x-am-primary-key", "auto")
        if self.key_type not in ["required", "auto", "sequence"]:
            raise ApplicationException(
                500,
                "Invalid primary key type must be one of required, "
                + f"auto, sequence.  schema_object: {self.entity}, "
                + f"property: {self.name}, type: {self.type}",
            )

        self.sequence_name = (
            properties.get("x-am-sequence-name")
            if self.key_type == "sequence"
            else None
        )
        if self.key_type == "sequence" and not self.sequence_name:
            raise ApplicationException(
                500,
                "Sequence-based primary keys must have a sequence "
                + f"name. Schema object: {self.entity}, Property: {self.name}",
            )


class SchemaObject(OpenAPIElement):
    concurrency_property: Optional[SchemaObjectProperty]

    def __init__(self, entity: str, schema_object: Dict[str, Any]):
        super().__init__(schema_object)
        self.entity = entity
        self.schema_object = schema_object
        database = schema_object.get("x-am-database")
        if database:
            self.database = database.lower()
        self.properties = {}
        self.relations = {}
        self.primary_key = None
        self.initialize_properties()
        self.set_concurrency_property(schema_object)

    def initialize_properties(self):
        for property_name, prop in self.schema_object.get("properties", {}).items():
            assert (
                prop is not None
            ), f"Property is none entity: {self.entity}, property: {property_name}"
            self.process_property(property_name, prop)

    def process_property(self, property_name: str, prop: Dict[str, Any]):
        type = (
            prop.get("type")
            if "type" in prop
            else self.resolve_reference(prop.get("$ref", None)).get("type")
            if "$ref" in prop
            else None
        )
        if not type:
            raise ApplicationException(
                500,
                f"Cannot resolve type, object_schema: {self.entity}, property: {property_name}",
            )

        if type in ["object", "array"]:
            self.relations[property_name] = SchemaObjectAssociation(
                self.entity,
                property_name,
                {**(prop if type == "object" else prop["items"]), "type": type},
            )
        else:
            object_property = SchemaObjectProperty(self.entity, property_name, prop)
            self.properties[property_name] = object_property
            if object_property.is_primary_key:
                self.primary_key = SchemaObjectKey(self.entity, property_name, prop)

    def set_concurrency_property(self, prop: Dict[str, Any]):
        self.concurrency_property = None
        concurrency_prop_name = prop.get("x-am-concurrency-control", None)
        if concurrency_prop_name:
            try:
                self.concurrency_property = self.properties[concurrency_prop_name]
            except KeyError:
                raise ApplicationException(
                    500,
                    f"Concurrency control property does not exist. schema_object: {self.entity}, property: {concurrency_prop_name}",
                )

    @property
    def table_name(self) -> str:
        schema = self.schema_object.get("x-am-schema")
        return (
            f"{schema}." if schema else ""
        ) + f"{self.schema_object.get('x-am-table', self.entity)}"

    def get_property(self, property_name: str) -> Optional[SchemaObjectProperty]:
        return self.properties.get(property_name)

    def get_relation(self, property_name: str) -> SchemaObjectAssociation:
        try:
            return self.relations[property_name]
        except KeyError:
            raise ApplicationException(
                500, f"Unknown relation {property_name}, check api spec.subselect sql:"
            )


class ModelFactory:
    spec: dict

    @classmethod
    def load_yaml(cls, api_spec_path: str):
        log.info(f"api_spec_path: {api_spec_path}")
        if api_spec_path:
            with open(api_spec_path, "r") as yaml_file:
                spec = yaml.safe_load(yaml_file)
        cls.set_spec(spec)

    @classmethod
    def set_spec(cls, spec):
        cls.spec = spec
        cls.schema_objects = dict()

        schemas = cls.spec.get("components", {}).get("schemas", {})
        lower_schemas = dict()
        for name, schema in schemas.items():
            lower_schemas[name.lower] = schema
            cls.schema_objects[name.lower()] = schema
        cls.spec.get("components", {})["schemas"] = cls.schema_objects

        log.info(f"schemas: {cls.schema_objects.keys()}")

    @classmethod
    def get_schema_object(cls, name: str) -> SchemaObject:
        return SchemaObject(name, cls.schema_objects[name])

    @classmethod
    def get_schema_names(cls) -> list[str]:
        return list(cls.schema_objects.keys())

import yaml
from typing import Any, Dict, Optional, List, Union
from datetime import datetime
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger

log = logger(__name__)

methods_to_actions = {
    "get": "read",
    "post": "create",
    "update": "update",
    "delete": "delete",
}


class OpenAPIElement:
    def __init__(self, element: dict):
        self.element = element
        self.title = self.element.get("title", None)
        self.description = self.element.get("description", None)
        self.required = self.element.get("required", None)
        self.type = self.element.get("type", None)

    def resolve_reference(self, reference: Optional[str]) -> dict:
        log.info(f"resolve_reference: {reference}")
        if not reference:
            return {}

        try:
            current_element = ModelFactory.spec
            if not current_element:
                return {}

            for component in reference.lower().split("/"):
                if component == "#":
                    continue
                elif component in current_element:
                    current_element = current_element[component]
                else:
                    raise ApplicationException(500, f"Reference not found: {reference}")

            return current_element  # Ensure that the resolved reference is a dictionary
        except Exception as e:
            log.error(f"Exception: {e}")
            raise ApplicationException(500, f"Failed to resolve reference: {reference}")


class SchemaObjectProperty(OpenAPIElement):
    def __init__(self, entity: str, name: str, properties: Dict[str, Any]):
        super().__init__(properties)
        self.entity = entity
        self.name = name
        self.properties = properties
        log.info(f"properties: {self.properties}")
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

    @property
    def default(self):
        log.info(f"properties: {self.properties}")
        return self.properties.get("default")

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


class SchemaObjectAssociation(OpenAPIElement):
    def __init__(self, entity: str, name: str, properties: Dict[str, Any]):
        super().__init__(properties)
        log.debug(f"entity: {entity}, name: {name}, properties: {properties}")
        assert all(arg is not None for arg in (entity, name, properties))
        self.entity = entity
        self.name = name
        self._properties = properties

    @property
    def child_property(self) -> "SchemaObjectProperty":
        child_property = self._properties.get("x-am-child-property", None)
        if not child_property:
            return self.child_schema_object.primary_key
        return self.child_schema_object.get_property(child_property)

    @property
    def parent_property(self) -> "SchemaObjectProperty":
        parent = self._properties.get("x-am-parent-property", None)
        parent_schema_object = ModelFactory.get_schema_object(self.entity)
        if parent:
            return parent_schema_object.get_property(parent)
        return parent_schema_object.primary_key

    @property
    def child_schema_object(self) -> "SchemaObject":
        schema_name = self._properties["$ref"].split("/")[-1]
        return ModelFactory.get_schema_object(schema_name)


class SchemaObject(OpenAPIElement):
    _properties: Dict[str, SchemaObjectProperty]
    _relations: Dict[str, SchemaObjectAssociation]
    _concurrency_property: Optional[SchemaObjectProperty]

    def __init__(self, entity: str, schema_object: Dict[str, Any]):
        super().__init__(schema_object)
        self.entity = entity
        self.schema_object = schema_object
        database = schema_object.get("x-am-database")
        if database:
            self.database = database.lower()
        self.primary_key = None

    @property
    def properties(self) -> Dict[str, SchemaObjectProperty]:
        if not hasattr(self, "_properties"):
            self._resolve_properties()
        return self._properties

    @property
    def relations(self) -> Dict[str, SchemaObjectAssociation]:
        if not hasattr(self, "_relations"):
            self._resolve_properties()
        return self._relations

    def _resolve_properties(self):
        self._properties = dict()
        self._relations = dict()
        for property_name, prop in self.schema_object.get("properties", {}).items():
            assert (
                prop is not None
            ), f"Property is none entity: {self.entity}, property: {property_name}"
            object_property = self._resolve_property(property_name, prop)
            if object_property:
                self._properties[property_name] = object_property

    def _resolve_property(self, property_name: str, prop: Dict[str, Any]):
        if "$ref" in prop:
            ref = self.resolve_reference(prop.get("$ref", None))
            type = ref.get("type")
        else:
            type = prop.get("type")

        if not type:
            raise ApplicationException(
                500,
                f"Cannot resolve type, object_schema: {self.entity}, property: {property_name}",
            )

        if type in ["object", "array"]:
            self._relations[property_name] = SchemaObjectAssociation(
                self.entity,
                property_name,
                {**(prop if type == "object" else prop["items"]), "type": type},
            )
        else:
            object_property = SchemaObjectProperty(self.entity, property_name, prop)
            if object_property.is_primary_key:
                self.primary_key = SchemaObjectKey(self.entity, property_name, prop)
            return object_property

        return None

    @property
    def concurrency_property(self) -> Optional[SchemaObjectProperty]:
        if not hasattr(self, "_concurrency_property"):
            concurrency_prop_name = self.schema_object.get(
                "x-am-concurrency-control", None
            )
            if concurrency_prop_name:
                try:
                    self._concurrency_property = self.properties[concurrency_prop_name]
                except KeyError:
                    raise ApplicationException(
                        500,
                        f"Concurrency control property does not exist. schema_object: {self.entity}, property: {concurrency_prop_name}",
                    )
            else:
                self._concurrency_property = None
        return self._concurrency_property

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


class PathOperation(OpenAPIElement):
    def __init__(self, path: str, method: str, path_operation: Dict[str, Any]):
        super().__init__(path_operation)
        self.path = path
        self.method = method
        self.path_operation = path_operation

    @property
    def database(self) -> str:
        return self.path_operation["x-am-database"]

    @property
    def sql(self) -> str:
        return self.path_operation["x-am-sql"]

    @property
    def inputs(self) -> Dict[str, SchemaObjectProperty]:
        if not hasattr(self, "_inputs"):
            self._inputs = dict()
            self._inputs.update(
                self._extract_properties(self.path_operation, "requestBody")
            )
            self._inputs.update(
                self._extract_properties(self.path_operation, "parameters")
            )
        return self._inputs

    @property
    def outputs(self) -> Dict[str, SchemaObjectProperty]:
        if not hasattr(self, "_outputs"):
            self._outputs = self._extract_properties(self.path_operation, "responses")
        return self._outputs

    def _extract_properties(
        self, operation: Dict[str, Any], section: str
    ) -> Dict[str, SchemaObjectProperty]:
        properties = {}
        if section == "requestBody" and "requestBody" in operation:
            content = operation["requestBody"].get("content", {})
            for name, property in content.items():
                properties[name] = SchemaObjectProperty(self.path, name, property)
        elif section == "parameters" and "parameters" in operation:
            content = operation["parameters"]
            for property in content:
                properties[property["name"]] = SchemaObjectProperty(
                    self.path, property["name"], property
                )
        elif section == "responses" and "responses" in operation:
            for status_code, response in operation["responses"].items():
                content = response.get("content", {})
                for name, property in content.items():
                    properties[name] = SchemaObjectProperty(self.path, name, property)
        return properties

    def _get_schema_properties(
        self, schema: Dict[str, Any], param_name: str = None
    ) -> Dict[str, SchemaObjectProperty]:
        properties = {}
        schema_ref = schema.get("$ref")
        if schema_ref:
            schema = self.resolve_reference(schema_ref)
        if "properties" in schema:
            for prop_name, prop_spec in schema["properties"].items():
                properties[prop_name] = SchemaObjectProperty(
                    self.path, prop_name, prop_spec
                )
        elif param_name:
            properties[param_name] = SchemaObjectProperty(self.path, param_name, schema)
        return properties


class ModelFactory:
    spec: dict
    schema_objects: Dict[str, SchemaObject] = {}
    path_operations: Dict[str, PathOperation] = []

    @classmethod
    def load_yaml(cls, api_spec_path: str):
        log.info(f"api_spec_path: {api_spec_path}")
        if api_spec_path:
            with open(api_spec_path, "r") as yaml_file:
                spec = yaml.safe_load(yaml_file)
        cls.set_spec(spec)

    @classmethod
    def set_spec(cls, spec: dict):
        cls.spec = spec
        cls.schema_objects = {}

        schemas = cls.spec.get("components", {}).get("schemas", {})
        for name, schema in schemas.items():
            if "x-am-database" in schema:
                cls.schema_objects[name.lower()] = schema

        log.info(f"schemas: {cls.schema_objects.keys()}")

        cls.initialize_schema_objects()
        cls.initialize_path_operations()

    @classmethod
    def initialize_schema_objects(cls):
        for name, schema in cls.schema_objects.items():
            cls.schema_objects[name] = SchemaObject(name, schema)

    @classmethod
    def initialize_path_operations(cls):
        paths = cls.spec.get("paths", {})
        cls.path_operations = {}
        for path, operations in paths.items():
            for method, operation in operations.items():
                if "x-am-database" in operation:
                    cls.path_operations[
                        f"{path.lstrip('/')}:{methods_to_actions[method.lower()]}"
                    ] = PathOperation(path, method, operation)

    @classmethod
    def get_schema_object(cls, name: str) -> SchemaObject:
        if name not in cls.schema_objects:
            cls.schema_objects[name] = SchemaObject(name, cls.schema_objects[name])

        return cls.schema_objects[name]

    @classmethod
    def get_schema_names(cls) -> List[str]:
        return list(cls.schema_objects.keys())

    @classmethod
    def get_path_operations(cls) -> Dict[str, PathOperation]:
        return cls.path_operations

    @classmethod
    def get_path_operation(cls, name: str, action: str) -> PathOperation:
        log.info(f"name: {name}, action: {action}")
        log.info(f"path_operations: {cls.path_operations}")
        return cls.path_operations.get(f"{name}:{action}")

    @classmethod
    def get_api_object(
        cls, name: str, action: str
    ) -> Union[SchemaObject, PathOperation]:
        result = cls.get_path_operation(name, action)
        log.info(f"result: {result}")
        if not result:
            result = cls.get_schema_object(name)
        return result

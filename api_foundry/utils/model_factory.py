import re
import yaml
from typing import Any, Dict, Optional, List, Union, cast
from datetime import datetime
from api_foundry.utils.app_exception import ApplicationException
from api_foundry.utils.spec_handler import SpecificationHandler
from api_foundry.utils.logger import logger, DEBUG

log = logger(__name__)

methods_to_actions = {
    "get": "read",
    "post": "create",
    "update": "update",
    "delete": "delete",
}


class OpenAPIElement:
    def __init__(self, element: Dict[str, Any], spec: Dict[str, Any]):
        self.element = element
        self.spec = spec
        self.spec_handler = SpecificationHandler(spec)
        self.title = self.element.get("title", None)
        self.description = self.element.get("description", None)
        self.required = self.element.get("required", None)
        self.type = self.element.get("type", None)

    def get(
        self, key: Union[List[str], str], element=None, default: Optional[str] = None
    ) -> Optional[Any]:
        result = self.spec_handler.get(element if element else self.element, key)
        return result if result else default


class SchemaObjectProperty(OpenAPIElement):
    def __init__(
        self,
        operation_id: str,
        name: str,
        properties: Dict[str, Any],
        spec: Dict[str, Any],
    ):
        super().__init__(properties, spec)
        self.operation_id = operation_id
        self.name = name
        self.column_name = self.get("x-af-column-name") or name
        self.type = self.get("type") or "string"
        self.api_type = self.get("format") or self.type
        self.column_type = self.get("x-af-column-type") or self.api_type
        self.is_primary_key = self.get("x-af-primary-key") or False
        self.min_length = self.get("minLength")
        self.max_length = self.get("maxLength")
        self.pattern = self.get("pattern")

        self.concurrency_control = self.get("x-af-concurrency-control")
        if self.concurrency_control:
            self.concurrency_control = self.concurrency_control.lower()
            assert self.concurrency_control in [
                "uuid",
                "timestamp",
                "serial",
            ], (
                "Unrecognized version type, schema object: {self.operation_id}, "
                + f"property: {name}, version_type: {self.concurrency_control}"
            )

    @property
    def default(self):
        return self.get("default")

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
    def __init__(
        self,
        operation_id: str,
        name: str,
        properties: Dict[str, Any],
        spec: Dict[str, Any],
    ):
        super().__init__(operation_id, name, properties, spec)
        log.info(f"properties: {properties}")
        log.info(f"key_type: {self.get('x-af-primary-key')}")
        self.key_type = self.get("x-af-primary-key", default="auto")
        if self.key_type not in ["manual", "uuid", "auto", "sequence"]:
            raise ApplicationException(
                500,
                "Invalid primary key type must be one of auto, uuid, "
                + f"manual, sequence.  schema_object: {self.operation_id}, "
                + f"property: {self.name}, type: {self.type}",
            )

        self.sequence_name = (
            self.get("x-af-sequence-name") if self.key_type == "sequence" else None
        )
        if self.key_type == "sequence" and not self.sequence_name:
            raise ApplicationException(
                500,
                "Sequence-based primary keys must have a sequence "
                + f"name. Schema object: {self.operation_id}, Property: {self.name}",
            )


class SchemaObjectAssociation(OpenAPIElement):
    def __init__(
        self,
        operation_id: str,
        name: str,
        properties: Dict[str, Any],
        spec: Dict[str, Any],
    ):
        super().__init__(properties, spec)
        self.operation_id = operation_id
        self.name = name

    @property
    def child_property(self) -> "SchemaObjectProperty":
        child_property = self.get("x-af-child-property", None)

        return cast(
            SchemaObjectProperty,
            (
                self.child_schema_object.get_property(child_property)
                if child_property
                else self.child_schema_object.primary_key
            ),
        )

    @property
    def parent_property(self) -> "SchemaObjectProperty":
        parent_schema_object = ModelFactory.get_schema_object(self.operation_id)
        if not parent_schema_object:
            raise ApplicationException(
                500,
                (
                    "Parent schema object not found for relation"
                    + f"operation_id: {self.operation_id}, "
                    f"attribute: {self.name}"
                ),
            )
        parent = self.get("x-af-parent-property")
        return cast(
            SchemaObjectProperty,
            (
                parent_schema_object.get_property(parent)
                if parent
                else parent_schema_object.primary_key
            ),
        )

    @property
    def child_schema_object(self) -> "SchemaObject":
        if not hasattr(self, "_child_schema_object"):
            if "$ref" not in self.element:
                raise ApplicationException(
                    500,
                    f"Missing $ref, operation_id: {self.operation_id}, "
                    + f"attrbute: {self.name}",
                )
            schema_name = self.element["$ref"].split("/")[-1]
            self._child_schema_object = ModelFactory.get_schema_object(schema_name)
        return self._child_schema_object


class SchemaObject(OpenAPIElement):
    _properties: Dict[str, SchemaObjectProperty]
    _relations: Dict[str, SchemaObjectAssociation]
    _concurrency_property: Optional[SchemaObjectProperty]

    def __init__(
        self, operation_id: str, schema_object: Dict[str, Any], spec: Dict[str, Any]
    ):
        super().__init__(schema_object, spec)
        log.info(f"schema_object init: {schema_object}")
        self.operation_id = operation_id
        self.schema_object = schema_object
        database = schema_object.get("x-af-database")
        if database:
            self.database = database.lower()

    @property
    def properties(self) -> Dict[str, SchemaObjectProperty]:
        log.info("properties")
        if not hasattr(self, "_properties"):
            self._resolve_properties()
        return self._properties

    @property
    def relations(self) -> Dict[str, SchemaObjectAssociation]:
        log.info("relations")
        if not hasattr(self, "_relations"):
            self._resolve_properties()
        return self._relations

    @property
    def primary_key(self) -> SchemaObjectKey:
        log.info("primary_key")
        if not hasattr(self, "_primary_key"):
            self._resolve_properties()
        return self._primary_key

    def _resolve_properties(self):
        log.info("resolve_properties")
        self._properties = dict()
        self._relations = dict()
        for property_name, prop in cast(dict, self.get("properties")).items():
            log.info(f"name: {property_name}, prop: {prop}")
            assert prop is not None, (
                f"Property is none operation_id: {self.operation_id}, "
                + f"property: {property_name}"
            )  # noqa E501
            object_property = self._resolve_property(property_name, prop)
            if object_property:
                self._properties[property_name] = object_property

    def _resolve_property(self, property_name: str, prop: Dict[str, Any]):
        log.info("resolve property")
        type = self.get("type", prop, None)

        if not type:
            raise ApplicationException(
                500,
                f"Cannot resolve type, object_schema: {self.operation_id}, property: {property_name}",  # noqa E501
            )

        if type in ["object", "array"]:
            log.info(f"relations: {property_name}")
            self._relations[property_name] = SchemaObjectAssociation(
                self.operation_id,
                property_name,
                {
                    **(
                        prop
                        if type == "object"
                        else cast(dict, self.get("items", prop))
                    ),
                    "type": type,
                },
                self.spec,
            )
        else:
            object_property = SchemaObjectProperty(
                self.operation_id, property_name, prop, self.spec
            )
            if object_property.is_primary_key:
                self._primary_key = SchemaObjectKey(
                    self.operation_id, property_name, prop, self.spec
                )
            return object_property

        return None

    @property
    def concurrency_property(self) -> Optional[SchemaObjectProperty]:
        if not hasattr(self, "_concurrency_property"):
            concurrency_prop_name = self.schema_object.get(
                "x-af-concurrency-control", None
            )
            if concurrency_prop_name:
                try:
                    self._concurrency_property = self.properties[concurrency_prop_name]
                except KeyError:
                    raise ApplicationException(
                        500,
                        "Concurrency control property does not exist. "
                        + f"operation_id: {self.operation_id}, "
                        + f"property: {concurrency_prop_name}",
                    )
            else:
                self._concurrency_property = None
        return self._concurrency_property

    @property
    def table_name(self) -> str:
        schema = self.schema_object.get("x-af-schema")
        return (
            f"{schema}." if schema else ""
        ) + f"{self.schema_object.get('x-af-table', self.operation_id)}"

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
    def __init__(
        self,
        path: str,
        method: str,
        path_operation: Dict[str, Any],
        spec: Dict[str, Any],
    ):
        super().__init__(path_operation, spec)
        self.path = path
        self.method = method
        self.path_operation = path_operation
        self.spec = spec

    @property
    def database(self) -> str:
        return self.path_operation["x-af-database"]

    @property
    def sql(self) -> str:
        return self.path_operation["x-af-sql"]

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
        if section == "requestBody":
            for name, property in (self.get(["requestBody", "content"]) or {}).items():
                properties[name] = SchemaObjectProperty(
                    self.path, name, property, self.spec
                )
        elif section == "parameters":
            for property in self.get("parameters") or {}:
                properties[property["name"]] = SchemaObjectProperty(
                    self.path, property["name"], property, self.spec
                )
        elif section == "responses":
            responses = self.get("responses")
            if responses:
                pattern = re.compile(r"2\d{2}|2xx")
                for status_code, response in responses.items():
                    if pattern.fullmatch(status_code):
                        if log.isEnabledFor(DEBUG):
                            log.debug(f"response: {response}")
                        content = (
                            self.get(
                                [
                                    "content",
                                    "application/json",
                                    "schema",
                                    "items",
                                    "properties",
                                ],
                                response,
                            )
                            or {}
                        )
                        if log.isEnabledFor(DEBUG):
                            log.debug(f"content: {content}")
                        for name, property in content.items():
                            properties[name] = SchemaObjectProperty(
                                self.path, name, property, self.spec
                            )
        return properties

    def _get_schema_properties(
        self, schema: Dict[str, Any], param_name: Optional[str] = None
    ) -> Dict[str, SchemaObjectProperty]:
        properties = {}
        schema_ref = schema.get("$ref")
        if schema_ref:
            schema = self.resolve_reference(schema_ref)
        if "properties" in schema:
            for prop_name, prop_spec in schema["properties"].items():
                properties[prop_name] = SchemaObjectProperty(
                    self.path, prop_name, prop_spec, self.spec
                )
        elif param_name:
            properties[param_name] = SchemaObjectProperty(
                self.path, param_name, schema, self.spec
            )
        return properties


class ModelFactory:
    spec: dict
    schema_objects: Dict[str, SchemaObject] = {}
    path_operations: Dict[str, PathOperation] = {}

    @classmethod
    def load_yaml(cls, api_spec_path: str):
        if api_spec_path:
            with open(api_spec_path, "r") as yaml_file:
                spec = yaml.safe_load(yaml_file)
        cls.set_spec(spec)

    @classmethod
    def set_spec(cls, spec: dict):
        log.info("set_spec")
        cls.spec = spec
        cls.schema_objects = {}

        schemas = cls.spec.get("components", {}).get("schemas", {})
        for name, schema in schemas.items():
            if "x-af-database" in schema:
                log.info(f"schema_object: {name}")
                cls.schema_objects[name] = SchemaObject(name, schema, cls.spec)

        paths = cls.spec.get("paths", {})
        cls.path_operations = {}
        for path, operations in paths.items():
            for method, operation in operations.items():
                if "x-af-database" in operation:
                    cls.path_operations[
                        f"{path.lstrip('/')}:{methods_to_actions[method.lower()]}"
                    ] = PathOperation(path, method, operation, cls.spec)

    @classmethod
    def get_schema_object(cls, name: str) -> SchemaObject:
        return cls.schema_objects[name]

    @classmethod
    def get_schema_names(cls) -> List[str]:
        return list(cls.schema_objects.keys())

    @classmethod
    def get_path_operations(cls) -> Dict[str, PathOperation]:
        return cls.path_operations

    @classmethod
    def get_path_operation(cls, name: str, action: str) -> Optional[PathOperation]:
        return cls.path_operations.get(f"{name}:{action}")

    @classmethod
    def get_api_object(
        cls, name: str, action: str
    ) -> Union[SchemaObject, PathOperation]:
        result = cls.get_path_operation(name, action)
        if not result:
            result = cls.get_schema_object(name)
        return result

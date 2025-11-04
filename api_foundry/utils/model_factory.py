import re
from typing import Any, Dict, Optional

from cloud_foundry import logger

from api_foundry.utils.app_exception import ApplicationException
from api_foundry.utils.schema_validator import validate_permissions

log = logger(__name__)


# Mapping of HTTP methods to CRUD-like actions
METHODS_TO_ACTIONS = {
    "get": "read",
    "post": "create",
    "put": "update",
    "patch": "update",
    "delete": "delete",
}

SUPPORTED_TYPES = {
    "string",
    "integer",
    "number",
    "boolean",
    "date",
    "date-time",
    "time",
    # Note: OpenAPI uses base type 'number' with optional
    # format 'float'/'double'. These formats are accepted and
    # normalized to api_type='number' while preserving the
    # original format in a separate attribute for mapping.
    "uuid",
    "array",
    "object",
}


class OpenAPIElement:
    """
    Base class for OpenAPI elements like schema properties and
    associations.
    """

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the OpenAPI element to a dictionary, including nested
        properties.
        """
        return {
            k: (v.to_dict() if isinstance(v, OpenAPIElement) else v)
            for k, v in self.__dict__.items()
            if v is not None  # Exclude items with a value of None
        }


class SchemaObjectProperty(OpenAPIElement):
    """
    Represents a property of a schema object in the OpenAPI
    specification.
    """

    def __init__(self, schema_name: str, name: str, prop: Dict[str, Any]):
        super().__init__()
        self.api_name = name
        # Base OpenAPI type and format
        base_type = prop.get("type") or "string"
        api_format = prop.get("format")
        # Preserve numeric formats (float/double) but normalize api_type
        # to 'number'
        if base_type == "number" and api_format in {"float", "double"}:
            self.api_type = "number"
            self.numeric_format = api_format
        else:
            # Maintain prior behavior for date/date-time/time/uuid by
            # allowing format as type
            self.api_type = api_format or base_type
            self.numeric_format = None
        # Validate the raw OpenAPI 'type' first to catch invalid base types
        raw_type = prop.get("type")
        if raw_type is not None and raw_type not in {
            "string",
            "integer",
            "number",
            "boolean",
            "array",
            "object",
        }:
            raise ApplicationException(
                500,
                (
                    f"Property: {name} in schema object: {schema_name} "
                    f"of type: {raw_type} is not a valid type"
                ),
            )
        if self.api_type not in SUPPORTED_TYPES:
            raise ApplicationException(
                500,
                (
                    f"Property: {name} in schema object: {schema_name} "
                    f"of type: {self.api_type} is not a valid type"
                ),
            )
        self.column_name = prop.get("x-af-column-name") or name
        # Choose column type. If user didn't specify x-af-column-type and this
        # is a numeric with a float/double format, apply a sensible default
        # (Postgres: float -> real, double -> double precision).
        if prop.get("x-af-column-type"):
            self.column_type = prop.get("x-af-column-type")
        elif base_type == "number" and self.numeric_format in {
            "float",
            "double",
        }:
            self.column_type = (
                "real" if self.numeric_format == "float" else "double precision"
            )
        else:
            self.column_type = prop.get("type") or "string"
        self.required = prop.get("required", False)
        self.min_length = prop.get("minLength", None)
        self.max_length = prop.get("maxLength", None)
        self.pattern = prop.get("pattern", None)
        self.default = prop.get("default", None)
        self.key_type = None
        self.sequence_name = None
        self.concurrency_control = self._concurrency_control(schema_name, prop)
        # For embedded objects/arrays
        self.sub_properties: Optional[Dict[str, SchemaObjectProperty]] = None
        self.items_sub_properties: Optional[Dict[str, SchemaObjectProperty]] = None

    def _concurrency_control(self, schema_name: str, prop_dict: dict) -> Optional[str]:
        concurrency_control = prop_dict.get("x-af-concurrency-control", None)
        if concurrency_control:
            concurrency_control = concurrency_control.lower()
            assert concurrency_control in [
                "uuid",
                "timestamp",
                "serial",
            ], (
                f"Invalid concurrency control type '{concurrency_control}' "
                + f"in schema object '{schema_name}', "
                + f"property '{self.api_name}'"
            )
        return concurrency_control


class SchemaObjectKey(SchemaObjectProperty):
    """Represents a primary key in a schema object."""

    def __init__(self, schema_name: str, name: str, properties: Dict[str, Any]):
        super().__init__(schema_name, name, properties)
        self.key_type = properties.get("x-af-primary-key", "auto")

        if self.key_type not in ["manual", "uuid", "auto", "sequence"]:
            raise ApplicationException(
                500,
                (
                    f"Invalid primary key type '{self.key_type}' "
                    + f"in schema object '{schema_name}', "
                    + f"property '{self.api_name}'"
                ),
            )

        self.sequence_name = (
            properties.get("x-af-sequence-name")
            if self.key_type == "sequence"
            else None
        )
        if self.key_type == "sequence" and not self.sequence_name:
            raise ApplicationException(
                500,
                (
                    "Sequence-based primary keys must have a sequence name in "
                    + f"schema object '{schema_name}', "
                    + f"property '{self.api_name}'"
                ),
            )


class SchemaObjectAssociation(OpenAPIElement):
    """Represents an association (relationship) between schema objects."""

    def __init__(self, name: str, prop: Dict[str, Any], parent_key):
        super().__init__()
        self.api_name = name
        self.api_type = prop["type"]

        self.schema_name = (
            prop["items"]["$ref"] if self.api_type == "array" else prop["$ref"]
        ).split("/")[-1]

        self.child_property = prop.get("x-af-child-property", None)
        self.parent_property = prop.get("x-af-parent-property", parent_key)


class SchemaObject(OpenAPIElement):
    """Represents a schema object in the OpenAPI specification."""

    def __init__(self, api_name: str, schema_object: Dict[str, Any]):
        super().__init__()
        self.api_name = api_name
        self.database = schema_object.get("x-af-database", "").lower()
        self.table_name = self._get_table_name(schema_object)
        self.properties = self._resolve_properties(schema_object)
        self.primary_key = self._get_primary_key(schema_object)
        self.relations = self._resolve_relations(schema_object)
        self.concurrency_property = self._get_concurrency_property(schema_object)
        self.permissions = self._get_permissions(schema_object)

    def _get_table_name(self, schema_object: dict) -> str:
        schema = schema_object.get("x-af-schema")
        table_name = schema_object.get("x-af-table", self.api_name)
        return f"{schema}.{table_name}" if schema else table_name

    def _resolve_properties(
        self, schema_object: dict
    ) -> Dict[str, SchemaObjectProperty]:
        properties = {}
        for property_name, prop in schema_object.get("properties", {}).items():
            object_property = self._resolve_property(property_name, prop)
            if object_property:
                properties[property_name] = object_property
        return properties

    def _resolve_property(
        self, property_name: str, prop: Dict[str, Any]
    ) -> Optional[SchemaObjectProperty]:
        # Validate raw OpenAPI base type early to catch invalid types
        # like 'float'
        raw_type = prop.get("type")
        if raw_type is not None and raw_type not in {
            "string",
            "integer",
            "number",
            "boolean",
            "array",
            "object",
        }:
            raise ApplicationException(
                500,
                (
                    f"Property: {property_name} in schema object: "
                    f"{self.api_name} of type: {raw_type} is not a valid type"
                ),
            )
        # If $ref is present, treat as relation
        if "$ref" in prop:
            return None
        prop_type = prop.get("type")
        # Embedded object
        if prop_type == "object":
            if "properties" in prop:
                # Recursively resolve sub-properties
                sub_properties = {}
                for sub_name, sub_prop in prop["properties"].items():
                    sub_properties[sub_name] = self._resolve_property(
                        sub_name, sub_prop
                    )
                # Store as a SchemaObjectProperty with nested sub_properties
                obj = SchemaObjectProperty(self.api_name, property_name, prop)
                obj.sub_properties = sub_properties
                return obj
            else:
                # Generic object property
                return SchemaObjectProperty(self.api_name, property_name, prop)
        # Array
        if prop_type == "array":
            items = prop.get("items", {})
            if "$ref" in items:
                return None  # relation
            if items.get("type") == "object" and "properties" in items:
                # Array of embedded objects
                sub_properties = {}
                for sub_name, sub_prop in items["properties"].items():
                    sub_properties[sub_name] = self._resolve_property(
                        sub_name, sub_prop
                    )
                obj = SchemaObjectProperty(self.api_name, property_name, prop)
                obj.items_sub_properties = sub_properties
                return obj
            else:
                # Array of primitives
                return SchemaObjectProperty(self.api_name, property_name, prop)
        # Primitive property
        return SchemaObjectProperty(self.api_name, property_name, prop)

    def _resolve_relations(
        self, schema_object: dict
    ) -> Dict[str, SchemaObjectAssociation]:
        relations = {}
        for property_name, prop in schema_object.get("properties", {}).items():
            # Direct $ref (object relation)
            if "$ref" in prop:
                relations[property_name.lower()] = SchemaObjectAssociation(
                    property_name, prop, self.primary_key
                )
            # Array of $ref (array relation)
            elif prop.get("type") == "array" and "$ref" in prop.get("items", {}):
                relations[property_name.lower()] = SchemaObjectAssociation(
                    property_name, prop, self.primary_key
                )
        return relations

    def _get_concurrency_property(self, schema_object: dict) -> Optional[str]:
        concurrency_property_name = schema_object.get("x-af-concurrency-control")
        if (
            concurrency_property_name
            and concurrency_property_name not in self.properties
        ):
            raise ApplicationException(
                500,
                (
                    "Invalid concurrency property: "
                    f"{concurrency_property_name} not found in properties."
                ),
            )
        return concurrency_property_name

    def _get_primary_key(self, schema_object: dict) -> Optional[str]:
        for property_name, properties in schema_object.get("properties", {}).items():
            if "x-af-primary-key" in properties:
                prop_obj = self.properties[property_name]
                prop_obj.key_type = properties.get("x-af-primary-key", "auto")

                if prop_obj.key_type not in [
                    "manual",
                    "uuid",
                    "auto",
                    "sequence",
                ]:
                    raise ApplicationException(
                        500,
                        (
                            f"Invalid primary key type '{prop_obj.key_type}' "
                            + f"in schema object '{self.api_name}'"
                            + f", property '{property_name}'"
                        ),
                    )

                if prop_obj.key_type == "sequence":
                    prop_obj.sequence_name = properties.get("x-af-sequence-name", None)
                    if not prop_obj.sequence_name:
                        raise ApplicationException(
                            500,
                            (
                                "Sequence-based primary keys must have a "
                                "sequence name "
                                + f"in schema object '{self.api_name}', "
                                + f"property '{property_name}'"
                            ),
                        )
                return property_name
        return None

    def _get_permissions(self, schema_object: dict) -> dict:
        """Extract permissions from schema using x-af-permissions only.

        Expects provider -> action -> role -> rule format.
        Also normalizes action names so 'create'/'update' map to 'write'.
        """
        raw_permissions = schema_object.get("x-af-permissions") or {}

        def normalize_actions(actions: Dict[str, Any]) -> Dict[str, Any]:
            result: Dict[str, Any] = {}
            for action, value in actions.items():
                key = "write" if action in ("create", "update") else action
                result[key] = value
            return result

        normalized: Dict[str, Any] = {}
        if isinstance(raw_permissions, dict):
            # Expected format: provider -> action -> role -> rule
            for provider, actions in raw_permissions.items():
                if isinstance(actions, dict):
                    normalized[provider] = normalize_actions(actions)
                else:
                    normalized[provider] = actions

        if normalized:
            validate_permissions(normalized)
        return normalized or {}

    def to_dict(self) -> Dict[str, Any]:
        """Recursively convert this schema object and its properties."""
        data = super().to_dict()
        data["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        data["relations"] = {k: v.to_dict() for k, v in self.relations.items()}
        if self.concurrency_property:
            data["concurrency_property"] = self.concurrency_property
        return data


class PathOperation(OpenAPIElement):
    """
    Represents a single operation (method) on a path in the OpenAPI
    specification.
    """

    def __init__(self, path: str, method: str, path_operation: Dict[str, Any]):
        super().__init__()
        self.entity = path.lower().rsplit("/", 1)[-1]
        self.action = METHODS_TO_ACTIONS[method]
        self.database = path_operation["x-af-database"]
        self.sql = path_operation["x-af-sql"]
        self.inputs = self.get_inputs(path_operation)
        self.outputs = self._extract_properties(path_operation, "responses")
        self.permissions = self._get_permissions(path_operation)

    def get_inputs(
        self, path_operation: Dict[str, Any]
    ) -> Dict[str, SchemaObjectProperty]:
        result = {}
        result = self._extract_properties(path_operation, "requestBody")
        result.update(self._extract_properties(path_operation, "parameters"))
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Recursively convert this path operation and its fields."""
        data = super().to_dict()
        data["inputs"] = {k: v.to_dict() for k, v in self.inputs.items()}
        data["outputs"] = {k: v.to_dict() for k, v in self.outputs.items()}
        return data

    def _extract_properties(
        self, path_operation: Dict[str, Any], section: str
    ) -> Dict[str, SchemaObjectProperty]:
        properties = {}
        if section == "requestBody":
            for name, prop_schema in (
                path_operation.get("requestBody", {}).get("content", {}) or {}
            ).items():
                properties[name] = SchemaObjectProperty(self.entity, name, prop_schema)
        elif section == "parameters":
            for param in path_operation.get("parameters", {}) or []:
                properties[param["name"]] = SchemaObjectProperty(
                    self.entity, param["name"], param
                )
        elif section == "responses":
            responses = path_operation.get("responses", {})
            pattern = re.compile(r"2\d{2}|2xx")
            for status_code, response in responses.items():
                if pattern.fullmatch(status_code):
                    content = (
                        response.get("content", {})
                        .get("application/json", {})
                        .get("schema", {})
                        .get("items", {})
                        .get("properties", {})
                    )
                    for name, out_schema in content.items():
                        properties[name] = SchemaObjectProperty(
                            self.entity, name, out_schema
                        )
        return properties

    def _get_permissions(self, path_operation: dict) -> dict:
        """
        Extract permissions from a path operation using x-af-permissions
        only. Expects provider -> action -> role -> rule format.
        Also normalizes action names so 'create'/'update' map to 'write'.
        """
        raw_permissions = path_operation.get("x-af-permissions") or {}

        def normalize_actions(actions: Dict[str, Any]) -> Dict[str, Any]:
            result: Dict[str, Any] = {}
            for action, value in actions.items():
                key = "write" if action in ("create", "update") else action
                result[key] = value
            return result

        normalized: Dict[str, Any] = {}
        if isinstance(raw_permissions, dict):
            # Expected format: provider -> action -> role -> rule
            for provider, actions in raw_permissions.items():
                if isinstance(actions, dict):
                    normalized[provider] = normalize_actions(actions)
                else:
                    normalized[provider] = actions

        if normalized:
            validate_permissions(normalized)
        return normalized or {}


class ModelFactory:
    """Factory class to load and process OpenAPI specifications into models."""

    def __init__(self, spec: dict):
        self.spec = self.resolve_all_refs(spec)
        self.schema_objects = self._load_schema_objects()
        self.path_operations = self._load_path_operations()

    def resolve_reference(self, ref: str, base_spec: Dict[str, Any]) -> Any:
        """Resolve a single $ref reference."""
        ref_parts = ref.lstrip("#/").split("/")
        result = base_spec
        for part in ref_parts:
            result = result.get(part)
            if result is None:
                raise KeyError(
                    f"Reference part '{part}' not found in the OpenAPI spec."
                )
        return result

    def merge_dicts(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two dictionaries. The override values take precedence."""
        merged = base.copy()  # Start with base values
        # Override with any values from the second dict
        merged.update(override)
        return merged

    def resolve_all_refs(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively resolve all $ref references in an OpenAPI
        specification.
        """

        def resolve(obj: Any) -> Any:
            if isinstance(obj, dict):
                if "$ref" in obj:
                    # Resolve the reference
                    resolved_ref = self.resolve_reference(obj["$ref"], spec)
                    # Merge the resolved reference with the original object
                    # (so we keep attributes like x-af-child-property)
                    return self.merge_dicts(resolved_ref, obj)
                # Recursively resolve other properties
                return {k: resolve(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [resolve(v) for v in obj]
            return obj

        return resolve(spec)

    def _load_schema_objects(self) -> Dict[str, SchemaObject]:
        """Loads all schema objects from the OpenAPI specification."""
        schema_objects = {}
        schemas = self.spec.get("components", {}).get("schemas", {})
        for name, schema in schemas.items():
            if "x-af-database" in schema:
                schema_objects[name] = SchemaObject(name, schema)
        return schema_objects

    def _load_path_operations(self) -> Dict[str, PathOperation]:
        """Loads all path operations from the OpenAPI specification."""
        path_operations = {}
        paths = self.spec.get("paths", {})
        for path, methods in paths.items():
            for method, operation in methods.items():
                if "x-af-database" in operation:
                    path_operation = PathOperation(path, method, operation)
                    path_operations[
                        f"{path_operation.entity}_{path_operation.action}"
                    ] = path_operation
        return path_operations

    def get_config_output(self) -> Dict[str, Any]:
        """Generates and returns the configuration output."""
        log.info("path_operations: %s", self.path_operations)
        return {
            "schema_objects": {
                name: obj.to_dict() for name, obj in self.schema_objects.items()
            },
            "path_operations": {
                name: obj.to_dict() for name, obj in self.path_operations.items()
            },
        }

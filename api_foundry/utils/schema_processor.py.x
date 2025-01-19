import re
from typing import Any, Dict, Optional
from api_foundry.utils.app_exception import ApplicationException
from api_foundry.utils.logger import logger
from api_foundry.utils.schema_validator import validate_x_af_security

log = logger(__name__)

SUPPORTED_TYPES = {"string", "integer", "boolean", "array", "object"}

class Permissions:
    """
    Handles role-based security permissions for schema objects.
    """

    def __init__(self, x_af_security: dict):
        validate_x_af_security(x_af_security)
        self.security = x_af_security

    def can(self, role: str, action: str, property_name: str) -> bool:
        """
        Checks if a role is allowed to perform a specific action on a property.

        Args:
            role (str): The role to check.
            action (str): The action ('read', 'write', 'delete') to check.
            property_name (str): The property name to check permissions for.

        Returns:
            bool: True if the role is allowed to perform the action, otherwise False.
        """
        role_permissions = self.security.get(role, {})
        if action in {"read", "write"}:
            regex = role_permissions.get(action, "")
            return bool(re.match(regex, property_name))
        if action == "delete":
            return role_permissions.get(action, False)
        return False


class SchemaProcessor:
    """
    Processes an OpenAPI specification into schema objects and path operations.

    Responsible for resolving references, validating schemas, managing keys,
    handling concurrency management, and role-based permissions.
    """

    def __init__(self, spec: dict):
        self.spec = self._resolve_all_refs(spec)
        self.schema_objects = self._load_schema_objects()
        self.path_operations = self._load_path_operations()

    def _resolve_reference(self, ref: str, base_spec: Dict[str, Any]) -> Any:
        ref_parts = ref.lstrip("#/").split("/")
        result = base_spec
        for part in ref_parts:
            result = result.get(part)
            if result is None:
                raise KeyError(f"Reference part '{part}' not found in the OpenAPI spec.")
        return result

    def _merge_dicts(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        merged = base.copy()
        merged.update(override)
        return merged

    def _resolve_all_refs(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        cache = {}

        def resolve(obj: Any) -> Any:
            if isinstance(obj, dict):
                if "$ref" in obj:
                    ref = obj["$ref"]
                    if ref not in cache:
                        resolved_ref = self._resolve_reference(ref, spec)
                        cache[ref] = self._merge_dicts(resolved_ref, obj)
                    return cache[ref]
                return {k: resolve(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [resolve(v) for v in obj]
            return obj

        return resolve(spec)

    def _load_schema_objects(self) -> Dict[str, Any]:
        schema_objects = {}
        schemas = self.spec.get("components", {}).get("schemas", {})
        for name, schema in schemas.items():
            if "x-af-database" in schema:
                schema_objects[name] = self._process_schema_object(name, schema)
        return schema_objects

    def _process_schema_object(self, name: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        permissions = Permissions(schema["x-af-permissions"]) if "x-af-permissions" in schema else None
        properties = self._get_schema_properties(name, schema)
        primary_key = self._get_primary_key(name, schema, properties)
        relations = self._get_relations(name, schema, primary_key)
        concurrency_property = self._get_concurrency_property(schema, properties)

        return {
            "api_name": name,
            "database": schema.get("x-af-database", "").lower(),
            "table_name": schema.get("x-af-table", name),
            "properties": properties,
            "primary_key": primary_key,
            "relations": relations,
            "concurrency_property": concurrency_property,
            "permissions": permissions,
        }


    def _get_schema_properties(self, schema_name: str, schema_object: Dict[str, Any]) -> Dict[str, Any]:
        properties = {}
        for property_name, prop in schema_object.get("properties", {}).items():
            prop_type = prop.get("type", "string")
            if prop_type in {"object", "array"}:
                continue
            properties[property_name] = self._validate_property(schema_name, property_name, prop)
        return properties

    def _validate_property(self, schema_name: str, property_name: str, property: Dict[str, Any]) -> Dict[str, Any]:
        log.info(f"property: {property}")
        if property.get("x-af-concurrency-control"):
            if property["x-af-concurrency-control"].lower() not in {"uuid", "timestamp", "serial"}:
                raise ApplicationException(
                    500, f"Invalid concurrency control '{property['x-af-concurrency-control']}' for property '{property_name}'."
                )

        api_type = property.get("format") or property.get("type")
        if api_type not in SUPPORTED_TYPES:
          raise ApplicationException(500, f"Unsupported type '{api_type}' in property '{property_name}'")

        return {
          "api_name": property_name,
          "column_name": property.get("x-af-column-name") or property_name,
          "api_type": property.get("format") or property.get("type"),
          "column_type": property.get("x-af-column-type") or property.get("format") or property.get("type"),
          "required": property.get("required", False),
          "min_length": property.get("minLength", None),
          "max_length": property.get("maxLength", None),
          "pattern": property.get("pattern", None),
          "default": property.get("default", None)
        }

    def _get_primary_key(self, schema_name: str, schema_object: Dict[str, Any], properties: Dict[str, Any]) -> Optional[str]:
        for property_name, prop in schema_object.get("properties", {}).items():
            if "x-af-primary-key" in prop:
                key_type = prop.get("x-af-primary-key", "auto")
                if key_type not in {"manual", "uuid", "auto", "sequence"}:
                    raise ApplicationException(
                        500, f"Invalid primary key type '{key_type}' for property '{property_name}' in schema '{schema_name}'."
                    )
                if key_type == "sequence" and not prop.get("x-af-sequence-name"):
                    raise ApplicationException(
                        500, f"Sequence primary key '{property_name}' must have 'x-af-sequence-name' defined in schema '{schema_name}'."
                    )
                return property_name
        return None

    def _get_relations(self, schema_name: str, schema_object: Dict[str, Any], primary_key: str) -> Dict[str, Any]:
        relations = {}
        for property_name, prop in schema_object.get("properties", {}).items():
            if prop.get("type") in {"object", "array"}:
                relation = {
                    "api_name": property_name,
                    "schema_name": (
                        prop["items"]["$ref"] if prop["type"] == "array" else prop["$ref"]
                    ).split("/")[-1],
                    "child_property": prop.get("x-af-child-property"),
                    "parent_property": prop.get("x-af-parent-property", primary_key),
                }
                relations[property_name] = relation
        return relations

    def _get_concurrency_property(self, schema_object: Dict[str, Any], properties: Dict[str, Any]) -> Optional[str]:
        concurrency_property_name = schema_object.get("x-af-concurrency-control")
        if concurrency_property_name and concurrency_property_name not in properties:
            raise ApplicationException(
                500, f"Invalid concurrency property '{concurrency_property_name}' not found in schema properties."
            )
        return concurrency_property_name

    def _load_path_operations(self) -> Dict[str, Any]:
        path_operations = {}
        paths = self.spec.get("paths", {})
        for path, methods in paths.items():
            for method, operation in methods.items():
                if "x-af-database" in operation:
                    path_operations[f"{path}_{method}"] = self._process_path_operation(
                        path, method, operation
                    )
        return path_operations

    def _process_path_operation(self, path: str, method: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "entity": path.lower().rsplit("/", 1)[-1],
            "action": method.lower(),
            "database": operation.get("x-af-database"),
            "sql": operation.get("x-af-sql"),
            "inputs": operation.get("requestBody", {}).get("content", {}),
            "outputs": operation.get("responses", {}),
        }

    def get_config_output(self) -> Dict[str, Any]:
        log.info(f"Processed {len(self.schema_objects)} schema objects.")
        log.info(f"Processed {len(self.path_operations)} path operations.")
        return {
            "schema_objects": self.schema_objects,
            "path_operations": self.path_operations,
        }

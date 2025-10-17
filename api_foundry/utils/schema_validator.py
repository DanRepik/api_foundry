# schema_validator.py

import re


def validate_permissions(permissions):
    """
    Validate the structure and semantics of `x-af-permissions`.

    Supported shape (refactored):
    {
        "default": {
            "read":  { <role>: <rule>, ... },
            "write": { <role>: <rule>, ... },
            "delete":{ <role>: <bool|deleteRule> , ... }
        },
        "<authenticator>": {   # optional targeted override blocks
            "read":  { <role>: <rule>, ... },
            "write": { <role>: <rule>, ... },
            "delete":{ <role>: <bool|deleteRule> , ... }
        }
    }

    Where for read/write operations, <rule> is either:
        - a string regex (field mask), or
        - an object: { "fields": <regex>, "where": <string-optional> }

    For delete, the rule is either:
        - a boolean, or
        - an object: { "allow": <bool>, "where": <string-optional> }
    """
    if not isinstance(permissions, dict):
        raise ValueError("`x-af-permissions` must be a dictionary.")

    # Helper to validate a single rule per action
    def _validate_rule(action: str, role_name: str, rule):
        if action in {"read", "write"}:
            # Accept either a string regex or an object
            # {properties: regex, where?: string}
            if isinstance(rule, str):
                try:
                    re.compile(rule)
                except re.error as e:
                    raise ValueError(
                        "Invalid regex pattern '"
                        + rule
                        + "' for action '"
                        + action
                        + "' in role '"
                        + role_name
                        + "': "
                        + str(e)
                    ) from e
            elif isinstance(rule, dict):
                # Support both for backward compatibility
                allowed_keys = {"properties", "fields", "where"}
                unknown = set(rule.keys()) - allowed_keys
                if unknown:
                    raise ValueError(
                        f"Unknown keys {unknown} in rule for role "
                        f"'{role_name}' action '{action}'. "
                        f"Allowed keys: {allowed_keys}."
                    )
                # Accept both 'properties' (preferred) and 'fields' (legacy)
                properties = rule.get("properties") or rule.get("fields")
                if not isinstance(properties, str):
                    raise ValueError(
                        f"Rule for role '{role_name}' action "
                        f"'{action}' must include 'properties' as a regex "
                        f"string."
                    )
                try:
                    re.compile(properties)
                except re.error as e:
                    raise ValueError(
                        "Invalid regex pattern in 'properties' for role '"
                        + role_name
                        + "' action '"
                        + action
                        + "': "
                        + str(e)
                    ) from e
                where = rule.get("where")
                if where is not None and not isinstance(where, str):
                    raise ValueError(
                        f"'where' must be a string when provided "
                        f"(role '{role_name}', action '{action}')."
                    )
            else:
                raise ValueError(
                    f"Rule for role '{role_name}' action '{action}' "
                    f"must be a string or object with 'properties' "
                    f"(and optional 'where')."
                )

        elif action == "delete":
            # Accept bool or object {allow: bool, where?: string}
            if isinstance(rule, bool):
                return
            if isinstance(rule, dict):
                allowed_keys = {"allow", "where"}
                unknown = set(rule.keys()) - allowed_keys
                if unknown:
                    raise ValueError(
                        f"Unknown keys {unknown} in delete rule for "
                        f"role '{role_name}'. Allowed keys: "
                        f"{allowed_keys}."
                    )
                allow = rule.get("allow")
                if not isinstance(allow, bool):
                    raise ValueError(
                        f"Delete rule for role '{role_name}' must "
                        f"include 'allow' as boolean."
                    )
                where = rule.get("where")
                if where is not None and not isinstance(where, str):
                    raise ValueError(
                        f"'where' must be a string when provided in "
                        f"delete rule (role '{role_name}')."
                    )
            else:
                raise ValueError(
                    (
                        "The value for action 'delete' in role '"
                        + role_name
                        + "' must be a boolean or object with 'allow'."
                    )
                )
        else:
            raise ValueError(
                f"Invalid action '{action}'. Allowed actions are "
                f"'read', 'write', and 'delete'."
            )

    # Detect legacy form: role -> {action: rule} or role with 'where'
    def _is_legacy_form(obj: dict) -> bool:
        if not obj:
            return False
        # If any top-level value is a dict where an action maps to a non-dict
        # rule (e.g., string/bool/object rule), it's the legacy form.
        # Also detect if there's a 'where' key at the role level.
        for v in obj.values():
            if isinstance(v, dict):
                # Check for role-level 'where' clause (hybrid approach)
                if "where" in v:
                    return True
                for k2, v2 in v.items():
                    actions = {"read", "write", "delete"}
                    if k2 in actions and not isinstance(v2, dict):
                        return True
        return False

    # Legacy path: {role: {read|write|delete: rule, where?: string}}
    if _is_legacy_form(permissions):
        for role_name, actions in permissions.items():
            if not isinstance(role_name, str):
                raise ValueError("Role names must be strings in legacy form.")
            if not isinstance(actions, dict):
                raise ValueError(
                    f"The value for role '{role_name}' must be a dictionary "
                    f"of actions."
                )
            for action, rule in actions.items():
                if action == "where":
                    # Validate role-level WHERE clause
                    if not isinstance(rule, str):
                        raise ValueError(
                            f"Role-level 'where' clause for role "
                            f"'{role_name}' must be a string."
                        )
                else:
                    _validate_rule(action, role_name, rule)
        return True

    # New form: {provider: {action: {role: rule}}}
    for provider_name, provider_rules in permissions.items():
        if not isinstance(provider_name, str):
            raise ValueError(
                "Top-level keys (e.g., 'default' or authenticator names) "
                "must be strings."
            )
        if not isinstance(provider_rules, dict):
            raise ValueError(
                f"The value for provider '{provider_name}' must be a "
                f"dictionary of operations."
            )

        for action, roles_map in provider_rules.items():
            if action not in {"read", "write", "delete"}:
                raise ValueError(
                    f"Invalid action '{action}' under provider "
                    f"'{provider_name}'. "
                    "Allowed actions are 'read', 'write', and 'delete'."
                )
            if not isinstance(roles_map, dict):
                # Backward compatibility: legacy form encountered under a
                # top-level key that looks like a provider. Treat the
                # provider_name as the role and validate the rule directly.
                _validate_rule(action, provider_name, roles_map)
                continue

            for role_name, rule in roles_map.items():
                if not isinstance(role_name, str):
                    raise ValueError(
                        f"Role name '{role_name}' under action "
                        f"'{action}' must be a string."
                    )
                _validate_rule(action, role_name, rule)

    return True

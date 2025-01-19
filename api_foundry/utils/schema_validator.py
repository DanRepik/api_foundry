# schema_validator.py

import re


def validate_permissions(permissions):
    """
    Validates the structure and semantics of the `x-af-permissions` attribute.

    Args:
        permissions (dict): The `permissions` attribute to validate.

    Returns:
        bool: True if the attribute is valid, otherwise raises a ValueError.

    Raises:
        ValueError: If the attribute structure or content is invalid.
    """
    if not isinstance(permissions, dict):
        raise ValueError("`x-af-permissions` must be a dictionary.")

    for role_name, actions in permissions.items():
        if not isinstance(role_name, str):
            raise ValueError(f"Role name '{role_name}' must be a string.")

        # Validate that actions is a dictionary
        if not isinstance(actions, dict):
            raise ValueError(f"Actions for role '{role_name}' must be a dictionary.")

        for action, regex in actions.items():
            # Validate allowed actions
            if action not in {"read", "write", "delete"}:
                raise ValueError(
                    f"Invalid action '{action}' for role '{role_name}'. "
                    "Allowed actions are 'read', 'write', and 'delete'."
                )

            # Validate regex patterns for property selection
            if action in {"read", "write"}:
                if not isinstance(regex, str):
                    raise ValueError(
                        f"The value for action '{action}' in role '{role_name}' must be a string."
                    )
                try:
                    re.compile(regex)
                except re.error as e:
                    raise ValueError(
                        f"Invalid regex pattern '{regex}' for action '{action}' in role '{role_name}': {e}"
                    )

            if action == "delete" and not isinstance(regex, bool):
                raise ValueError(
                    f"The value for action '{action}' in role '{role_name}' must be a boolean."
                )

    return True

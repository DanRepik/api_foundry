# schema_validator.py

import re


def validate_permissions(permissions):
    """
    Validate the structure and semantics of `x-af-permissions`.

    Expected shape:
    {
      <auth_handler>: {
        <role_name>: { "read": <regex>, "write": <regex>, "delete": <bool> },
        ...
      },
      ...
    }
    """
    if not isinstance(permissions, dict):
        raise ValueError("`x-af-permissions` must be a dictionary.")

    for handler_name, roles in permissions.items():
        if not isinstance(handler_name, str):
            raise ValueError("Authorization handler names must be strings.")
        if not isinstance(roles, dict):
            raise ValueError(
                (
                    "The value for handler '"
                    + handler_name
                    + "' must be a dictionary of roles."
                )
            )

        for role_name, actions in roles.items():
            if not isinstance(role_name, str):
                raise ValueError(f"Role name '{role_name}' must be a string.")
            if not isinstance(actions, dict):
                raise ValueError(
                    f"Actions for role '{role_name}' must be a dictionary."
                )

            for action, rule in actions.items():
                if action not in {"read", "write", "delete"}:
                    raise ValueError(
                        f"Invalid action '{action}' for role '{role_name}'. "
                        "Allowed actions are 'read', 'write', and 'delete'."
                    )

                if action in {"read", "write"}:
                    if not isinstance(rule, str):
                        raise ValueError(
                            (
                                "The value for action '"
                                + action
                                + "' in role '"
                                + role_name
                                + "' must be a string."
                            )
                        )
                    try:
                        re.compile(rule)
                    except re.error as e:
                        raise ValueError(
                            (
                                "Invalid regex pattern '"
                                + rule
                                + "' for action '"
                                + action
                                + "' in role '"
                                + role_name
                                + "': "
                                + str(e)
                            )
                        ) from e

                if action == "delete" and not isinstance(rule, bool):
                    raise ValueError(
                        (
                            "The value for action '"
                            + action
                            + "' in role '"
                            + role_name
                            + "' must be a boolean."
                        )
                    )

    return True

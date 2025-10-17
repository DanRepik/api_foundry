#!/usr/bin/env python3

import sys
import json
import jwt

# Add API Foundry to path
sys.path.insert(0, "/Users/clydedanielrepik/workspaces/api_foundry")

from tests.conftest import TEST_USERS


def print_token_analysis():
    """Print detailed analysis of the expected token"""

    user_config = TEST_USERS["clients"]["user_sales_associate"]

    print("=== TOKEN CONFIGURATION ANALYSIS ===")
    print(f"Client ID: {user_config['sub']}")
    print(f"Audience: {user_config['audience']}")
    print(f"Scope: {user_config['scope']}")
    print(f"Roles: {user_config['roles']}")
    print(f"Role type: {type(user_config['roles'])}")

    print("\n=== EXPECTED JWT CLAIMS ===")
    expected_claims = {
        "iss": "https://oauth.local/",  # Default issuer
        "sub": user_config["sub"],
        "aud": user_config["audience"],
        "scope": user_config["scope"],
        "roles": user_config["roles"],
        # Plus iat, exp timestamps
    }
    print(json.dumps(expected_claims, indent=2))

    print("\n=== OAUTH VALIDATOR CONTEXT ===")
    # From Simple OAuth Server token_validator.py:
    expected_context = {
        "sub": str(user_config["sub"]),
        "scope": str(user_config["scope"]),
        "roles": json.dumps(user_config["roles"]),  # JSON encoded!
        "groups": json.dumps([]),
        "permissions": json.dumps([]),
    }
    print(json.dumps(expected_context, indent=2))

    print("\n=== API FOUNDRY PERMISSIONS EXPECTED ===")
    expected_permissions = {"sales_associate": {"read": ".*", "write": ".*"}}
    print(json.dumps(expected_permissions, indent=2))

    print("\n=== ANALYSIS ===")
    print("1. The JWT should have 'roles': ['sales_associate']")
    print(
        "2. OAuth validator should pass 'roles': '[\"sales_associate\"]' (JSON string)"
    )
    print("3. API Foundry should decode the JSON and match 'sales_associate' role")
    print("4. Permission 'read: .*' should allow reading all album properties")
    print()
    print(
        "LIKELY ISSUE: Role claim not being properly decoded from JSON in the context"
    )
    print(
        "or there's a mismatch between the role name in the token vs. the permissions"
    )


if __name__ == "__main__":
    print_token_analysis()

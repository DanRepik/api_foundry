#!/usr/bin/env python3

import os
import sys
import json
import jwt
import requests
import time

# Add API Foundry to path
sys.path.insert(0, "/Users/clydedanielrepik/workspaces/api_foundry")

from tests.conftest import TEST_USERS


def get_token_content():
    """Get a token and decode it to see its contents"""

    # Start a minimal test to get API endpoint - we need to run the actual test
    print(
        "To debug this properly, we need to modify the token validator temporarily..."
    )
    print("The issue is likely in the JWT validation step")

    user_config = TEST_USERS["clients"]["user_sales_associate"]
    print(f"User config: {json.dumps(user_config, indent=2)}")

    print(f"Expected audience: {user_config['audience']}")
    print(f"Token scope: {user_config['scope']}")
    print(f"User roles: {user_config['roles']}")

    print("\nThe JWT validation fails with a 402 error.")
    print("Most likely causes:")
    print("1. Audience mismatch - stage name != 'chinook-api'")
    print("2. Issuer mismatch")
    print("3. Token signature validation failing")
    print("4. Scope validation logic has a bug")

    print("\nLet me create a modified token validator that logs more details...")


if __name__ == "__main__":
    get_token_content()

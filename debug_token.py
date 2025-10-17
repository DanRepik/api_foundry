#!/usr/bin/env python3

import jwt
import requests
import json
import pytest
import sys
import os

# Add the current directory to the path so we can import from tests
sys.path.insert(0, "/Users/clydedanielrepik/workspaces/api_foundry")


def decode_jwt_token(token):
    """Decode JWT token without verification to see its contents"""
    try:
        # Decode without verification to see the payload
        decoded = jwt.decode(token, options={"verify_signature": False})
        print("JWT Token Contents:")
        print(json.dumps(decoded, indent=2, default=str))
        return decoded
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None


def test_manual_request():
    """Manually test the album endpoint"""

    # We need to set up the test environment first
    from tests.conftest import TEST_USERS

    print("TEST_USERS configuration:")
    print(json.dumps(TEST_USERS, indent=2))

    # Get token endpoint - we'll have to construct it manually
    # The endpoint format we saw was: irmku3v3gy.execute-api.localhost.localstack.cloud:55186
    # But we need to start the infrastructure first

    print("\nTo test manually, we need the API endpoint from a running test...")
    print("The JWT token configuration looks correct - sales_associate has:")
    print("- scope: 'read:* write:*'")
    print("- roles: ['sales_associate']")
    print("- audience: '/chinook-api'")

    print("\nThe OpenAPI spec shows album endpoint has permissions:")
    print("- sales_associate: read: .*, write: .*")

    print("\nThe issue might be:")
    print("1. JWT token validation failing in the authorizer")
    print("2. Scope checking logic has a bug")
    print("3. Role-based permissions not working correctly")
    print("4. LocalStack specific issue with 402 error code")


if __name__ == "__main__":
    test_manual_request()

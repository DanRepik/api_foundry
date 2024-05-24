import requests
import pytest

# The API ID and stage name from the previous steps
API_ID = "nt5zecklg7"
STAGE_NAME = "dev"

# Base URL for the LocalStack API Gateway
BASE_URL = f"http://{API_ID}.execute-api.localhost.localstack.cloud:4566/{STAGE_NAME}"

def test_get_request():
    # Define the endpoint
    endpoint = "/album"

    print(BASE_URL + endpoint)

    # Send the GET request
    response = requests.get(BASE_URL + endpoint)

    # Validate the response status code
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Validate the response content
    json_response = response.json()
    expected_keys = ["id", "name", "value"]  # Replace with expected keys
    for key in expected_keys:
        assert key in json_response, f"Missing key '{key}' in response"

    # Additional validation (if necessary)
    assert json_response["id"] == 1, "Expected 'id' to be 1"
    assert isinstance(json_response["name"], str), "Expected 'name' to be a string"
    assert isinstance(json_response["value"], int), "Expected 'value' to be an integer"


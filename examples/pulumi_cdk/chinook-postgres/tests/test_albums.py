import json
import requests
from pytest import fixture
from pulumi import automation as auto

from api_maker.utils.logger import logger

log = logger(__name__)

def get_stack_output_value(stack_name: str, work_dir: str, output_name: str):
    # Create or select a stack
    try:
        stack = auto.select_stack(
            stack_name=stack_name,
            work_dir=work_dir,
        )

        # Refresh the stack to get the latest outputs
        stack.refresh(on_output=print)

        # Get the stack outputs
        outputs = stack.outputs()
    except auto.errors.CommandError:
        return None


    # Return the requested output value
    return outputs[output_name].value if output_name in outputs else None


# The API ID and stage name from the previous steps

API_ID = get_stack_output_value("local", ".", "gateway-api") #"nt5zecklg7"
print(f"api_id: {API_ID}")
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
    log.info(f"response: {response.text}")
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


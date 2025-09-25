import requests
import logging

log = logging.getLogger(__name__)


def test_stack_deployment(chinook_api_endpoint):
    assert chinook_api_endpoint is not None
    assert "execute-api.localhost.localstack.cloud" in chinook_api_endpoint


def test_chinook_api_stack_simple_request(chinook_api_endpoint):
    url = f"{chinook_api_endpoint}/album/1"
    response = requests.get(url)
    log.info(f"Response Status Code: {response.status_code}")
    log.info(f"Response: {response.text}")
    assert response.status_code == 200

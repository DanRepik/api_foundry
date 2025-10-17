import requests
import logging

log = logging.getLogger(__name__)


def test_stack_deployment(chinook_api_endpoint):
    assert chinook_api_endpoint is not None
    assert "execute-api.localhost.localstack.cloud" in chinook_api_endpoint


def test_chinook_api_stack_simple_request(chinook_api_endpoint):
    url = f"{chinook_api_endpoint}/employee/1"
    response = requests.get(url, timeout=10)
    assert response.status_code == 200

    expected_response = [
        {
            "address": "11120 Jasper Ave NW",
            "birth_date": "1962-02-18T00:00:00",
            "city": "Edmonton",
            "country": "Canada",
            "email": "andrew@chinookcorp.com",
            "employee_id": 1,
            "fax": "+1 (780) 428-3457",
            "first_name": "Andrew",
            "hire_date": "2002-08-14T00:00:00",
            "last_name": "Adams",
            "phone": "+1 (780) 428-9482",
            "postal_code": "T5K 2N1",
            "reports_to": None,
            "state": "AB",
            "title": "General Manager",
        }
    ]
    assert response.json() == expected_response


b'{"error": "invalid_client", "error_description": "Unknown client"}'


def test_sales_associate_can_access_albums(chinook_api_endpoint, sales_associate):
    url = f"{chinook_api_endpoint}/album"
    headers = {"Authorization": f"Bearer {sales_associate}"}
    response = requests.get(url, headers=headers, timeout=10)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

from datetime import datetime
import json
import os
import requests

from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger

from test_secrets_fixture_cp import gateway_endpoint, db_secrets

log = logger(__name__)


class TestCrudService:
    def test_crud_service(self, db_secrets, gateway_endpoint):
        """
        Integration test to check basic crud services.  Media type does not have
        a primary key so query strings are required.
        """
        # test insert/create
        # Send the POST request
        response = requests.post(
            gateway_endpoint + "/media_type",
            headers={"Content-Type": "application/json"},
            json={"media_type_id": 9000, "name": "X-Ray"},
        )
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert result[0]["name"] == "X-Ray"

        # test select/read
        response = requests.get(gateway_endpoint + "/media_type?media_type_id=9000")
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert result[0]["media_type_id"] == 9000
        assert result[0]["name"] == "X-Ray"

        # test update
        response = requests.put(
            gateway_endpoint + "/media_type?media_type_id=9000",
            headers={"Content-Type": "application/json"},
            json={"name": "Ray Gun"},
        )
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 1
        assert result[0]["name"] == "Ray Gun"

        # test delete
        response = requests.delete(gateway_endpoint + "/media_type?media_type_id=9000")

        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 1
        assert result[0]["media_type_id"] == 9000
        assert result[0]["name"] == "Ray Gun"

        # test select/read
        response = requests.get(gateway_endpoint + "/media_type?media_type_id=9000")
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 0

    def test_crud_with_timestamp_service(self, db_secrets, gateway_endpoint):
        """
        Integration test to check insert
        """
        # test insert/create
        response = requests.post(
            gateway_endpoint + "/invoice",
            headers={"Content-Type": "application/json"},
            json={
                "invoice_date": datetime.now().isoformat(),
                "customer_id": 2,
                "billing_address": "address",
                "billing_city": "billing_city",
                "billing_state": "billing_state",
                "billing_country": "billing_country",
                "billing_postal_code": "code",
                "total": "3.15",
            },
        )
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert result[0]["billing_address"] == "address"

        creation_date = result[0]["last_updated"]
        invoice_id = result[0]["invoice_id"]

        # test select/read
        response = requests.get(f"{gateway_endpoint}/invoice/{invoice_id}")
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert result[0]["invoice_id"] == invoice_id
        assert result[0]["total"] == 3.15

        # try update without concurrency value. should fail
        response = requests.put(
            f"{gateway_endpoint}/invoice/{invoice_id}",
            headers={"Content-Type": "application/json"},
            json={"billing_address": "address"},
        )
        assert response.status_code == 404

        result = json.loads(response.text)
        log.info(f"result: {result}")

        # test update
        response = requests.put(
            f"{gateway_endpoint}/invoice/{invoice_id}/last_updated/{creation_date}",
            headers={"Content-Type": "application/json"},
            json={"billing_address": "updated address"},
        )
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 1
        assert result[0]["billing_address"] == "updated address"
        modified_date = result[0]["last_updated"]

        # try update with bad concurrency value. should fail
        response = requests.put(
            f"{gateway_endpoint}/invoice/{invoice_id}/last_updated/{creation_date}",
            headers={"Content-Type": "application/json"},
            json={"billing_address": "address"},
        )
        log.info(f"status_code: {response.status_code}")
        assert response.status_code == 400

        result = json.loads(response.text)
        log.info(f"result: {result}")

        # delete without concurrency value. should fail
        response = requests.delete(f"{gateway_endpoint}/invoice/{invoice_id}")
        log.info(f"status_code: {response.status_code}")
        assert response.status_code == 404

        log.info(f"result: {json.loads(response.text)}")

        response = requests.delete(
            f"{gateway_endpoint}/invoice/{invoice_id}/last_updated/{modified_date}"
        )
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 1
        assert result[0]["invoice_id"] == invoice_id
        assert result[0]["customer_id"] == 2

        # test select/read
        response = requests.get(f"{gateway_endpoint}/invoice/{invoice_id}")
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 0

    def test_crud_with_uuid_service(self, gateway_endpoint):
        """
        Integration test to check insert
        """
        # test insert/create
        response = requests.post(
            gateway_endpoint + "/customer",
            headers={"Content-Type": "application/json"},
            json={
                "first_name": "John",
                "last_name": "Doe",
                "company": "Acme Inc.",
                "address": "123 Main St",
                "city": "Anytown",
                "state": "California",
                "country": "United States",
                "postal_code": "12345",
                "phone": "123-456-7890",
                "fax": "123-456-7890",
                "email": "john.doe@example.com",
                "support_rep_id": 3,
            },
        )
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert result[0]["address"] == "123 Main St"

        customer_id = result[0]["customer_id"]
        creation_stamp = result[0]["version_stamp"]

        # test select/read
        response = requests.get(f"{gateway_endpoint}/customer/{customer_id}")
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 1
        assert result[0]["customer_id"] == customer_id
        assert result[0]["support_rep_id"] == 3

        # try update without concurrency value. should fail
        response = requests.put(
            f"{gateway_endpoint}/customer?customer_id={customer_id}",
            headers={"Content-Type": "application/json"},
            json={"address": "321 Broad St"},
        )
        assert response.status_code == 404
        log.info(f"result: {json.loads(response.text)}")

        # test update
        response = requests.put(
            f"{gateway_endpoint}/customer/{customer_id}/version_stamp/{creation_stamp}",
            headers={"Content-Type": "application/json"},
            json={"address": "321 Broad St"},
        )
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 1
        assert result[0]["address"] == "321 Broad St"
        modified_stamp = result[0]["version_stamp"]

        # test update again version stamp should be incorrect
        response = requests.put(
            f"{gateway_endpoint}/customer/{customer_id}/version_stamp/{creation_stamp}",
            headers={"Content-Type": "application/json"},
            json={"address": "321 Broad St"},
        )
        assert response.status_code == 400
        log.info(f"result: {json.loads(response.text)}")

        # test delete without version stamp
        response = requests.delete(
            f"{gateway_endpoint}/customer?customer_id={customer_id}"
        )
        assert response.status_code == 404
        log.info(f"result: {json.loads(response.text)}")

        # test delete incorrect version
        response = requests.delete(
            f"{gateway_endpoint}/customer/{customer_id}/version_stamp/{creation_stamp}"
        )
        assert response.status_code == 400
        log.info(f"result: {json.loads(response.text)}")

        # test delete
        response = requests.delete(
            f"{gateway_endpoint}/customer/{customer_id}/version_stamp/{modified_stamp}"
        )
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 1
        assert result[0]["customer_id"] == customer_id

        # test select/read
        response = requests.get(f"{gateway_endpoint}/customer/{customer_id}")
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 0

    def test_crud_with_version_number_service(self, gateway_endpoint):
        """
        Integration test to check insert
        """
        # test insert/create
        response = requests.post(
            gateway_endpoint + "/customer",
            headers={"Content-Type": "application/json"},
            json={
                "first_name": "John",
                "last_name": "Doe",
                "company": "Acme Inc.",
                "address": "123 Main St",
                "city": "Anytown",
                "state": "California",
                "country": "United States",
                "postal_code": "12345",
                "phone": "123-456-7890",
                "fax": "123-456-7890",
                "email": "john.doe@example.com",
                "support_rep_id": 3,
            },
        )
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert result[0]["address"] == "123 Main St"

        customer_id = result[0]["customer_id"]
        creation_stamp = result[0]["version_stamp"]

        # test select/read
        response = requests.get(f"{gateway_endpoint}/customer/{customer_id}")
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 1
        assert result[0]["customer_id"] == customer_id
        assert result[0]["support_rep_id"] == 3

        # try update without concurrency value. should fail
        response = requests.put(
            f"{gateway_endpoint}/customer?customer_id={customer_id}",
            headers={"Content-Type": "application/json"},
            json={"address": "321 Broad St"},
        )
        assert response.status_code == 404
        log.info(f"result: {json.loads(response.text)}")

        # test update
        response = requests.put(
            f"{gateway_endpoint}/customer/{customer_id}/version_stamp/{creation_stamp}",
            headers={"Content-Type": "application/json"},
            json={"address": "321 Broad St"},
        )
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 1
        assert result[0]["address"] == "321 Broad St"
        modified_stamp = result[0]["version_stamp"]

        # test update again version stamp should be incorrect
        response = requests.put(
            f"{gateway_endpoint}/customer/{customer_id}/version_stamp/{creation_stamp}",
            headers={"Content-Type": "application/json"},
            json={"address": "321 Broad St"},
        )
        assert response.status_code == 400
        log.info(f"result: {json.loads(response.text)}")

        # test delete without version stamp
        response = requests.delete(
            f"{gateway_endpoint}/customer?customer_id={customer_id}"
        )
        assert response.status_code == 404
        log.info(f"result: {json.loads(response.text)}")

        # test delete incorrect version
        response = requests.delete(
            f"{gateway_endpoint}/customer/{customer_id}/version_stamp/{creation_stamp}"
        )
        assert response.status_code == 400
        log.info(f"result: {json.loads(response.text)}")

        # test delete
        response = requests.delete(
            f"{gateway_endpoint}/customer/{customer_id}/version_stamp/{modified_stamp}"
        )
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 1
        assert result[0]["customer_id"] == customer_id

        # test select/read
        response = requests.get(f"{gateway_endpoint}/customer/{customer_id}")
        assert response.status_code == 200

        result = json.loads(response.text)
        log.info(f"result: {result}")

        assert len(result) == 0

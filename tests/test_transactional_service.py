
from datetime import datetime
import json
import os

import pytest

from test_connection_factory import secrets_map, install_secrets
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.model_factory import ModelFactory
from api_maker.utils.logger import logger
from api_maker.operation import Operation
from api_maker.services.transactional_service import TransactionalService

log = logger(__name__)

class TestTransactionalService():

  def test_create_service(self):
    """
    Integration test to check both 1:1 and 1:m associations
    """
    install_secrets()
    ModelFactory.load_spec()

    os.environ["SECRETS_MAP"] = secrets_map

    transactional_service = TransactionalService()
    operation = Operation(
            entity="invoice",
            action="read",
            query_params={"invoice_id": "363"},
            metadata_params={"_properties": ".* customer:.* line_items:.*"},
        )

    result = transactional_service.execute(operation)
    log.info(f"result: {result}")
    log.info(f"result: {json.dumps(result, indent=4)}")
    assert result[0]["invoice_id"] == 363
    assert result[0]["customer"]["customer_id"] == 28
    assert result[0]["line_items"][0]["invoice_id"] == 363
 
  def test_crud_with_timestamp_service(self):
    """
    Integration test to check insert
    """
    ModelFactory.load_spec()
    install_secrets()
    os.environ["SECRETS_MAP"] = secrets_map

    # test insert/create
    transactional_service = TransactionalService()
    operation = Operation(
            entity="invoice",
            action="create",
            store_params={
              "invoice_date":datetime.now().isoformat(),
              "customer_id": 2,
              "billing_address": "address",
              "billing_city": "billing_city",
              "billing_state": "billing_state",
              "billing_country": "billing_country",
              "billing_postal_code": "code",
              "total": "3.1459"
            }
        )

    result = transactional_service.execute(operation)
    log.info(f"result: {json.dumps(result, indent=4)}")
    assert result[0]["billing_address"] == "address"

    invoice_id = result[0]["invoice_id"]

    # test select/read
    operation = Operation(
            entity="invoice",
            action="read",
            query_params={"invoice_id": invoice_id},
            metadata_params={"_properties": ".* customer:.* line_items:.*"},
        )
    result = transactional_service.execute(operation)
    
    log.info(f"result: {result}")
    log.info(f"result: {json.dumps(result, indent=4)}")
    assert result[0]["invoice_id"] == invoice_id
    assert result[0]["customer"]["customer_id"] == 2
    assert len(result[0]["line_items"]) == 0

    invoice_id = result[0]["invoice_id"]

    # try update without concurrency value. should fail
    try:
      operation = Operation(
              entity="invoice",
              action="update",
              query_params={"invoice_id": invoice_id}
          )
      
      result = transactional_service.execute(operation)
      assert len(result) == 1
    except ApplicationException as e:
      assert e.message == "For updating concurrency managed schema objects the current version must be supplied as a query parameter.  schema_object: invoice, property: last_updated"

    # test update
    operation = Operation(
            entity="invoice",
            action="update",
            query_params={"invoice_id": invoice_id, "last_updated": result[0]["last_updated"]},
            store_params={"billing_address": "updated address"}
        )
    
    result = transactional_service.execute(operation)

    log.info(f"result: {json.dumps(result, indent=4)}")
    assert len(result) == 1
    assert result[0]["billing_address"] == "updated address"

    # test delete
    operation = Operation(
            entity="invoice",
            action="delete",
            query_params={"invoice_id": invoice_id, "last_updated": result[0]["last_updated"]}
        )
    
    result = transactional_service.execute(operation)

    log.info(f"result: {json.dumps(result, indent=4)}")
    assert len(result) == 1
    assert result[0]["invoice_id"] == invoice_id
    assert result[0]["customer_id"] == 2

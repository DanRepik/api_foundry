
import json
import pytest
import os

from test_connection_factory import secrets_map
from api_maker.utils.logger import logger
from api_maker.operation import Operation
from api_maker.services.transactional_service import TransactionalService

log = logger(__name__)

class TestTransactionalService():

  @pytest.mark.quick
  def test_transactional_service(self):
    os.environ["SECRETS_MAP"] = secrets_map

    transactional_service = TransactionalService()
    operation = Operation(
            entity="invoice",
            action="read",
            query_params={"invoice_id": "363"},
            metadata_params={"_properties": ".* customer:.*"},
        )

    result = transactional_service.execute(operation)
    log.info(f"result: {json.dumps(result, indent=4)}")
    assert False

import json
import os

import pytest

from test_connection_factory import secrets_map, install_secrets
from api_maker.utils.logger import logger
from api_maker.operation import Operation
from api_maker.services.transactional_service import TransactionalService

log = logger(__name__)

class TestTransactionalService():

  @pytest.mark.quick
  def test_transactional_service(self):
    install_secrets()
    os.environ["SECRETS_MAP"] = secrets_map

    transactional_service = TransactionalService()
    operation = Operation(
            entity="invoice",
            action="read",
            query_params={"invoice_id": "363"},
            metadata_params={"_properties": ".* customer:.*, line_items:.*"},
        )

    result = transactional_service.execute(operation)
    log.info(f"result: {json.dumps(result, indent=4)}")
    assert False
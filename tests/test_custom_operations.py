import pytest

from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.operation import Operation
from api_maker.services.transactional_service import TransactionalService

from test_fixtures import load_model, db_secrets  # noqa F401

log = logger(__name__)


@pytest.mark.integration
class TestCustomOperations:
    def test_top_albums(self, load_model, db_secrets):  # noqa F811
        result = TransactionalService().execute(
            Operation(
                entity="top_selling_albums",
                action="read",
                query_params={
                    "start": "2022-01-01T00:00:00",
                    "end": "2022-01-07T00:00:00",
                },
            )
        )

        log.debug(f"len: {len(result)}")
        invoice = result[0]
        log.debug(f"invoice: {invoice}")

        assert invoice["customer"]
        assert invoice["customer_id"] == invoice["customer"]["customer_id"]
        assert invoice["customer"]["city"] == "Boston"

from datetime import datetime
import json

from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger
from api_maker.operation import Operation
from api_maker.services.transactional_service import TransactionalService

from test_fixtures import load_model, db_secrets

log = logger(__name__)


class TestAssociationOperations:
    def test_object_property(self, load_model, db_secrets):
        result = TransactionalService().execute(
            Operation(
                entity="invoice",
                action="read",
                query_params={"invoice_id": 5},
                metadata_params={"properties": ".* customer:.*"},
            )
        )

        log.debug(f"len: {len(result)}")
        invoice = result[0]
        log.debug(f"invoice: {invoice}")

        assert invoice["customer"]
        assert invoice["customer_id"] == invoice["customer"]["customer_id"]
        assert invoice["customer"]["city"] == "Boston"

    def test_invalid_object_property(self, load_model, db_secrets):
        try:
            result = TransactionalService().execute(
                Operation(
                    entity="invoice",
                    action="read",
                    query_params={"invoice_id": 5},
                    metadata_params={"properties": ".* custom:.*"},
                )
            )
            assert False, "Missing exception"
        except ApplicationException as ae:
            assert ae.status_code == 400
            assert (
                ae.message
                == "Bad object associtiaon: invoice does not have a custom property"
            )

    def test_object_property_criteria(self, load_model, db_secrets):
        result = TransactionalService().execute(
            Operation(
                entity="invoice",
                action="read",
                query_params={"customer.customer_id": 5},
            )
        )

        log.debug(f"len: {len(result)}")
        assert len(result) == 7
        invoice = result[3]
        log.debug(f"invoice: {invoice}")

        assert "customer" not in invoice
        assert invoice["customer_id"] == 5
        assert invoice["billing_city"] == "Prague"

    def test_invalid_object_property_criteria(self, load_model, db_secrets):
        try:
            result = TransactionalService().execute(
                Operation(
                    entity="invoice",
                    action="read",
                    query_params={"custom.customer_id": 5},
                )
            )
            assert False, "Missing exception"
        except ApplicationException as ae:
            assert ae.status_code == 400
            assert (
                ae.message
                == "Invalid selection property invoice does not have a property custom."
            )

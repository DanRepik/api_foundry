import yaml
import json

from api_maker.utils.model_factory import ModelFactory
from api_maker.iac.gateway_doc import GatewapDocument
from api_maker.utils.logger import logger

log = logger(__name__)


class TestGatewayDoc:
    def test_gateway_document(self):
        ModelFactory.load_spec()
        gateway_doc = GatewapDocument(
            authentication_invoke_arn="authentication invoke", enable_cors=True
        )

        api_doc = gateway_doc.api_doc
        log.debug(f"self._api_doc {json.dumps(gateway_doc.api_doc, indent=4)}")

        assert False

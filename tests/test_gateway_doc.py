import yaml
import json

from api_maker.utils.model_factory import ModelFactory
from api_maker.iac.gateway_doc import GatewayDocument
from api_maker.utils.logger import logger

log = logger(__name__)


class TestGatewayDoc:
    def test_gateway_document(self):
        ModelFactory.load_spec()
        gateway_doc = GatewayDocument(
            function_name="function_name",
            function_invoke_arn="invoke_arn", 
            enable_cors=True
        )

        with open("./test.yaml", "w") as file:
            file.write(yaml.dump(gateway_doc.api_doc, indent=4))

        #        api_doc = gateway_doc.api_doc
        #        log.debug(f"self._api_doc { yaml.dump(gateway_doc.api_doc, indent=4)}")

        assert False

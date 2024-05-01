
from api_maker.utils.model_factory import ModelFactory
from api_maker.utils.logger import logger

log = logger(__name__)
class TestModelFactory():

    def test_get_schema_object(self):
        schema = ModelFactory.get_schema_object("invoice")
        
        log.info(f"relations: {schema.relations}")
        log.info(f"properties: {schema.properties}")
        log.info(f"table_name: {schema.table_name}")
        assert schema.table_name == "invoice"



from api_maker.utils.model_factory import ModelFactory
from api_maker.utils.logger import logger

log = logger(__name__)

class TestModelFactory():

    def test_get_schema_object(self):
        schema = ModelFactory.get_schema_object("employee")
        log.info(f"schemas: {schema}")

        properties = schema.get("properties")
        assert properties is not None
        assert properties.get("employee_id", None) is not None

    def test_get_operation(self):
        pass

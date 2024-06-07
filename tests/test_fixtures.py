import pytest

from api_maker.utils.model_factory import ModelFactory

@pytest.fixture
def load_model():
    ModelFactory.load_yaml("resources/chinook_api.yaml")

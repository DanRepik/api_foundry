import os
import yaml

from api_maker.utils.logger import logger

log = logger(__name__)


class ModelFactory:

    __document = None

    @classmethod
    def get_schema_object(cls, entity: str):
        return cls.__get_document_spec().get("components", {}).get("schemas", {}).get(entity)

    @classmethod
    def get_operation(cls, entity: str, operation: str):
        return cls.__get_document_spec().get("paths", {}).get(entity, {}).get(operation)
    
    @classmethod
    def __get_document_spec(cls):
        if not cls.__document:
            with open(os.environ["API_SPEC"], 'r') as yaml_file:
                cls.__document = yaml.safe_load(yaml_file)
            
            components = cls.__document.get("components", {})
            schemas = components.get("schemas", {})
            components["schemas"] = {key.lower().replace('_', '-'): value for key, value in schemas.items()}

        log.info(f"document: {cls.__document}")
        return cls.__document


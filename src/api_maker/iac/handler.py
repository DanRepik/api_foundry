import json
import logging
import os
from api_maker.utils.app_exception import ApplicationException
from api_maker.adapters.gateway_adapter import GatewayAdapter
from api_maker.utils.model_factory import ModelFactory

log = logging.getLogger(__name__)

def lambda_handler(event, _):
    log.info(f"event: {event}")
    try:
        factory = ModelFactory.load_spec("/var/task/api_spec.yaml")
        adapter = GatewayAdapter()
        response = adapter.process_event(event)

        # Ensure the response conforms to API Gateway requirements
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response)
        }
    except ApplicationException as e:
        log.error(f"exception: {e}", exc_info=True)
        return {
            "isBase64Encoded": False,
            "statusCode": e.status_code,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": f"exception: {e}"})
        }
    except Exception as e:
        log.error(f"exception: {e}", exc_info=True)
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": f"exception: {e}"})
        }

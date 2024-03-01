import abc
import json

from api_maker.operation import Operation
from api_maker.utils.logger import logger
from api_maker.services.service import Service

log = logger(__name__)

class Adapter(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, __subclass: type) -> bool:
        return (hasattr(__subclass, 'marshal')
                and callable(__subclass.marshal)
                and hasattr(__subclass, 'umarshal')
                and callable(__subclass.unmarshal))

    def __init__(self, service: Service) -> None:
        self.service = service
        
    def unmarshal(self, event) -> Operation:
        """
        Unmarshal the event in a tuple for processing

        Parameters:
        - event (dict): Lambda event object.

        Returns:
        - Operation containing the entity, action, and parameters 
        """
        raise NotImplementedError

    def marshal(self, result: list[dict]):
        """
        Marshal the result into a event response

        Parameters:
        - result (list): the data set to return in the response

        Returns:
        - the event response
        """
        return result

    def process_event(self, service: Service, event):
        """
        Process Lambda event using a domain function.

        Parameters:
        - service_function (callable): The service function to be executed.
        - event (dict): Lambda event object.

        Returns:
        - any: Result of the domain function.
        """
        operation = self.unmarshal(event)

        result = self.service.execute(operation)
        log.debug(f"adapter result: {result}")

        return self.marshal(result)

import abc

from api_maker.connectors.connector import Connector
from api_maker.operation import Operation


class DAO(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, __subclass: type) -> bool:
        return hasattr(__subclass, "execute") and callable(__subclass.execute)

    def execute(self, connector: Connector, operation: Operation) -> list[dict]:
        raise NotImplementedError


class DAOAdapter(DAO):
    def execute(self, connector: Connector, operation: Operation) -> list[dict]:
        return super().execute(connector, operation)

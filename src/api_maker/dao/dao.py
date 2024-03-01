import abc


class DAO(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, __subclass: type) -> bool:
        return hasattr(__subclass, "execute") and callable(__subclass.execute)

    def execute(
        self,
        *,
        entity: str,
        operation: str,
        store_params: dict,
        query_params: dict,
        metadata_params: dict,
    ) -> list[dict]: 
        raise NotImplementedError


class DAOAdapter(DAO):
    def execute(
        self,
        *,
        entity: str,
        operation: str,
        store_params: dict,
        query_params: dict,
        metadata_params: dict,
    ) -> list[dict]:
        return super().execute(
            entity=entity,
            operation=operation,
            store_params=store_params,
            query_params=query_params,
            metadata_params=metadata_params,
        )

class Operation:
    def __init__(
        self,
        *,
        operation_id: str,
        action: str,
        query_params={},
        store_params={},
        metadata_params={},
    ):
        self.operation_id = operation_id
        self.action = action
        self.query_params = query_params
        self.store_params = store_params
        self.metadata_params = metadata_params

from typing import List, Dict
import re

from api_maker.dao.sql_query_handler import SQLQueryHandler
from api_maker.utils.model_factory import (
    SchemaObject,
    SchemaObjectProperty,
    PathOperation,
)
from api_maker.operation import Operation
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.logger import logger

log = logger(__name__)


class SQLCustomQueryHandler(SQLQueryHandler):
    def __init__(
        self, operation: Operation, path_operation: PathOperation, engine: str
    ) -> None:
        super().__init__(operation, engine)
        self.path_operation = path_operation

    @property
    def sql(self) -> str:
        if not hasattr(self, "_sql"):
            self._compile()
        return self._sql

    @property
    def placeholders(self) -> Dict[str, SchemaObjectProperty]:
        if not hasattr(self, "_placeholders"):
            self._compile()
        return self._placeholders

    @property
    def select_list_columns(self) -> List[SchemaObjectProperty]:
        raise NotImplementedError()

    #        return self.path_operation.outputs

    def _compile(self):
        placeholder_pattern = re.compile(r":(\w+)")
        self._placeholders = dict()
        result_sql = placeholder_pattern.sub(
            self._get_placeholder_text, self.path_operation.sql
        )
        self._sql = re.sub(r"\s+", " ", result_sql).strip()

    def _get_placeholder_text(self, match) -> str:
        placeholder_name = match.group(1)
        property = self.path_operation.inputs.get(placeholder_name)
        if not property:
            raise ApplicationException(
                500,
                f"Input parameter not defined for the placeholder: {placeholder_name}",
            )

        value = (
            self.operation.query_params[placeholder_name]
            if placeholder_name in self.operation.query_params
            else property.default
        )
        log.info(
            f"placeholder_name: {placeholder_name}, value: {value}, default: {property.default}"
        )
        log.info(f"placeholders: {self.generate_placeholders(property, value)}")
        self._placeholders.update(self.generate_placeholders(property, value))
        return self.placeholder(property, placeholder_name)

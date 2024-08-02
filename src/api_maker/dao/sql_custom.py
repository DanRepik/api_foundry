from datetime import date, datetime
from typing import Any, List, Dict
from io import UnsupportedOperation
import re

from api_maker.dao.sql_generator import SQLOperation
from api_maker.utils.model_factory import (
    SchemaObject,
    SchemaObjectProperty,
    PathOperation,
)
from api_maker.operation import Operation
from api_maker.utils.logger import logger

log = logger(__name__)


class CustomSQLGenerator(SQLOperation):
    def __init__(
        self, operation: Operation, path_operation: PathOperation, engine: str
    ) -> None:
        super().__init__(operation, engine)
        self.path_operation = path_operation
        self._placeholders = None

    @property
    def sql(self) -> str:
        return self._replace_placeholders(self.path_operation.sql)

    @property
    def placeholders(self) -> Dict[str, SchemaObjectProperty]:
        if not self._placeholders:
            self._placeholders = {}
            for param in self.path_operation.inputs:
                self._placeholders[param.name] = param
        return self._placeholders

    @property
    def select_list_columns(self) -> List[SchemaObjectProperty]:
        return self.path_operation.outputs

    def _replace_placeholders(self, sql: str) -> str:
        placeholder_pattern = re.compile(r":(\w+)")
        return placeholder_pattern.sub(self._get_placeholder_text, sql)

    def _get_placeholder_text(self, match) -> str:
        placeholder_name = match.group(1)
        if placeholder_name in self.placeholders:
            return self.placeholder(self.placeholders[placeholder_name])
        else:
            raise UnsupportedOperation(
                f"Placeholder {placeholder_name} not found in path operation inputs."
            )

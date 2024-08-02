from api_maker.operation import Operation
from api_maker.dao.sql_custom import CustomSQLGenerator
from api_maker.utils.model_factory import PathOperation
from api_maker.utils.logger import logger
from test_fixtures import load_model  # noqa F401

log = logger(__name__)


class TestSQLGenerator:
    def test_custom_sql(self, load_model):  # noqa F811
        sql_operation = CustomSQLGenerator(
            Operation(
                entity="invoice",
                action="read",
                query_params={"invoice_id": "24", "total": "gt::5"},
            ),
            PathOperation(
                path="/top-selling-albums",
                method="get",
                path_operation={
                    "summary": "Get top-selling albums",
                    "description": "Returns the top 10 selling albums within a specified datetime range.",
                    "x-am-database": "chinook",
                    "x-am-sql": """
                        SELECT
                            a.album_id as album_id,
                            a.title AS album_title,
                            COUNT(il.invoice_line_id) AS total_sold
                        FROM
                            invoice_line il
                        JOIN
                            track t ON il.track_id = t.track_id
                        JOIN
                            album a ON t.album_id = a.album_id
                        WHERE
                            i.invoice_date >= :start
                            AND i.invoice_date <= :end
                        GROUP BY
                            a.title
                        ORDER BY
                            total_sold DESC
                        LIMIT 10;
                      """,
                    "parameters": [
                        {
                            "in": "query",
                            "name": "start",
                            "schema": {"type": "string", "format": "date-time"},
                            "required": True,
                            "description": "Start datetime for the sales period.",
                        },
                        {
                            "in": "query",
                            "name": "end",
                            "schema": {"type": "string", "format": "date-time"},
                            "required": True,
                            "description": "End datetime for the sales period.",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "A list of top-selling albums",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "album_id": {
                                                    "type": "integer",
                                                    "description": "The id of the album",
                                                },
                                                "album_title": {
                                                    "type": "string",
                                                    "description": "The title of the album",
                                                },
                                                "total_sold": {
                                                    "type": "integer",
                                                    "description": "The number of albums sold",
                                                },
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
            ),
            "postgres",
        )

        log.info(
            f"sql: {sql_operation.sql}, placeholders: {sql_operation.placeholders}"
        )

        assert False

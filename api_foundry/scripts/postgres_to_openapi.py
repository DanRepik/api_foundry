import psycopg2
import psycopg2.extras
import yaml
import argparse


class PostgresSchemaToOpenAPI:
    def __init__(self, host, database, user, password, schema="public"):
        self.connection = psycopg2.connect(
            host=host, database=database, user=user, password=password
        )
        self.schema = schema
        self.database = database

    def get_tables(self):
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (self.schema,))
            tables = cursor.fetchall()
        return [table[0] for table in tables]

    def get_columns(self, table_name):
        query = """
        SELECT column_name, data_type, is_nullable, character_maximum_length,
               (SELECT ccu.table_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = %s
                AND tc.table_schema = %s
                AND ccu.column_name = c.column_name
                LIMIT 1) AS foreign_table
        FROM information_schema.columns AS c
        WHERE table_schema = %s AND table_name = %s
        """
        with self.connection.cursor(
            cursor_factory=psycopg2.extras.DictCursor
        ) as cursor:
            cursor.execute(query, (table_name, self.schema, self.schema, table_name))
            columns = cursor.fetchall()
        return columns

    def get_primary_keys(self, table_name):
        query = """
        SELECT kcu.column_name, c.is_identity
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.columns c
            ON c.table_schema = tc.table_schema
            AND c.table_name = tc.table_name
            AND c.column_name = kcu.column_name
        WHERE tc.constraint_type = 'PRIMARY KEY'
        AND tc.table_name = %s
        AND tc.table_schema = %s
        """
        with self.connection.cursor(
            cursor_factory=psycopg2.extras.DictCursor
        ) as cursor:
            cursor.execute(query, (table_name, self.schema))
            pks = cursor.fetchall()

        primary_keys = {}
        for pk in pks:
            primary_keys[pk["column_name"]] = (
                "auto" if pk["is_identity"] == "YES" else "manual"
            )

        return primary_keys

    def map_data_type(self, data_type):
        type_mapping = {
            "character varying": {"type": "string"},
            "varchar": {"type": "string"},
            "character": {"type": "string"},
            "char": {"type": "string"},
            "text": {"type": "string"},
            "integer": {"type": "integer"},
            "bigint": {"type": "integer"},
            "smallint": {"type": "integer"},
            "numeric": {"type": "number"},
            "real": {"type": "number"},
            "double precision": {"type": "number"},
            "boolean": {"type": "boolean"},
            "date": {"type": "string", "format": "date"},
            "timestamp without time zone": {"type": "string", "format": "date-time"},
            "timestamp with time zone": {"type": "string", "format": "date-time"},
            "uuid": {"type": "string", "format": "uuid"},
        }
        return type_mapping.get(data_type, {"type": "string"})

    def generate_openapi_schema(self):
        openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Generated API", "version": "1.0.0"},
            "components": {"schemas": {}},
        }

        tables = self.get_tables()
        foreign_key_map = {}  # To track foreign key relationships

        for table in tables:
            columns = self.get_columns(table)
            primary_keys = self.get_primary_keys(table)
            properties = {}
            required = []

            for column in columns:
                column_name = column["column_name"]
                column_info = self.map_data_type(column["data_type"])

                if column_name in primary_keys:
                    column_info["x-af-primary-key"] = primary_keys[column_name]
                    if primary_keys[column_name] == "auto":
                        column_info[
                            "description"
                        ] = f"Unique identifier for the {table}. Read only"

                if (
                    column_info["type"] == "string"
                    and "character_maximum_length" in column
                    and column["character_maximum_length"]
                ):
                    column_info["maxLength"] = column["character_maximum_length"]

                if column["is_nullable"] == "NO":
                    required.append(column_name)

                properties[column_name] = column_info

                if column["foreign_table"]:
                    foreign_table = column["foreign_table"]
                    properties[foreign_table] = {
                        "$ref": f"#/components/schemas/{foreign_table}",
                        "x-af-parent-property": column_name,
                        "description": f"{foreign_table.capitalize()} associated with the {table}.",
                    }

                    # Track the foreign key relationship
                    if foreign_table not in foreign_key_map:
                        foreign_key_map[foreign_table] = []
                    foreign_key_map[foreign_table].append((table, column_name))

            schema_object = {
                "type": "object",
                "properties": properties,
                "required": required,
                "x-af-database": self.database,
            }
            openapi_schema["components"]["schemas"][table] = schema_object

        # Add array properties for foreign key relationships
        for parent_table, foreign_keys in foreign_key_map.items():
            if parent_table in openapi_schema["components"]["schemas"]:
                for child_table, foreign_key in foreign_keys:
                    openapi_schema["components"]["schemas"][parent_table]["properties"][
                        f"{child_table}_items"
                    ] = {
                        "type": "array",
                        "items": {
                            "$ref": f"#/components/schemas/{child_table}",
                            "x-af-child-property": foreign_key,
                        },
                        "description": f"List of {child_table} items associated with this {parent_table}.",
                    }

        return openapi_schema

    def save_openapi_schema(self, file_path):
        openapi_schema = self.generate_openapi_schema()
        with open(file_path, "w") as file:
            yaml.dump(openapi_schema, file, sort_keys=False)

    def close_connection(self):
        self.connection.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate OpenAPI schema from PostgreSQL database schema."
    )
    parser.add_argument("--host", required=True, help="PostgreSQL database host")
    parser.add_argument("--database", required=True, help="PostgreSQL database name")
    parser.add_argument("--user", required=True, help="PostgreSQL database user")
    parser.add_argument(
        "--password", required=True, help="PostgreSQL database password"
    )
    parser.add_argument(
        "--schema", default="public", help="PostgreSQL schema (default: public)"
    )
    parser.add_argument(
        "--output", required=True, help="Output file path for the OpenAPI schema"
    )

    args = parser.parse_args()

    converter = PostgresSchemaToOpenAPI(
        host=args.host,
        database=args.database,
        user=args.user,
        password=args.password,
        schema=args.schema,
    )
    converter.save_openapi_schema(args.output)
    converter.close_connection()


if __name__ == "__main__":
    main()

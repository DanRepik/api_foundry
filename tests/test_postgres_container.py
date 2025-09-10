import uuid
import psycopg2
import pytest

# Import fixtures from local module


def test_postgres_container_basic_crud(postgres_container):
    dsn = postgres_container["dsn"]
    table = f"t_{uuid.uuid4().hex[:8]}"

    conn = psycopg2.connect(dsn)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(f"CREATE TABLE {table} (id SERIAL PRIMARY KEY, name TEXT NOT NULL)")
                cur.execute(f"INSERT INTO {table} (name) VALUES (%s), (%s)", ("alice", "bob"))
                cur.execute(f"SELECT name FROM {table} ORDER BY id")
                rows = cur.fetchall()
        assert [r[0] for r in rows] == ["alice", "bob"]
    finally:
        with conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table}")
        conn.close()


@pytest.mark.usefixtures("postgres_container_no_teardown")
def test_postgres_container_no_teardown_connect(postgres_container_no_teardown):
    # Ensure we can connect to the long-lived container
    dsn = postgres_container_no_teardown["dsn"]
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            assert cur.fetchone()[0] == 1
    finally:
        conn.close()
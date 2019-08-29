import sqlite3

import pytest

from iprefer.db import user_queries


@pytest.fixture
def conn():
    conn = sqlite3.connect(':memory:')
    user_queries.create_schema(conn)
    return conn

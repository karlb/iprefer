from pathlib import Path
import sqlite3
from itertools import chain

from flask.cli import AppGroup
import aiosql  # type: ignore

importer_cli = AppGroup('import')

queries = aiosql.from_path(Path(__file__).parent / "dataset.sql", "sqlite3")


def save_dataset(filename, items):
    conn = sqlite3.connect(filename)
    queries.create_schema(conn)
    print(
        conn.executemany("""
                INSERT INTO item(name, item_id, lat, lon)
                VALUES (:name, :item_id, :lat, :lon)
            """,
            items
        ).rowcount,
        'items inserted'
    )
    print(
        conn.executemany(
            'INSERT INTO tags(item_id, key, value) VALUES (?, ?, ?)',
            chain.from_iterable(
                chain.from_iterable(
                    ((item['item_id'], key, val) for val in values)
                    for key, values in item['tags'].items()
                )
                for item in items
            )
        ).rowcount,
        'tags inserted'
    )
    conn.commit()


from . import osm
from . import wikidata

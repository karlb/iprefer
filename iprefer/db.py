from dataclasses import dataclass
import sqlite3
import json

import aiosql
from flask import g

from .iprefer import app

DATABASE = 'data/data.sqlite3'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.execute("ATTACH DATABASE 'data/user.sqlite3' AS user")
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@dataclass
class Item:
    name: str
    item_id: int
    tags: dict
    rank: float

    def __post_init__(self):
        self.tags = json.loads(self.tags)

    def location_breadcrumb(self):
        return [
            (self.tags.get('addr:country', 'DE'), '#'),  # TODO: default
            (self.tags.get('addr:city', 'Berlin'), '#'),  # TODO: default
            (self.tags.get('addr:suburb'), '#'),
            (self.tags['addr:street'], '#'),
        ]

    def amenity_breadcrumb(self):
        return [
            (self.tags['amenity'], '#'),
            (self.tags['cuisine'], '#'),
        ]

    def all_breadcrumbs(self):
        return [
            self.location_breadcrumb(),
            self.amenity_breadcrumb(),
        ]


queries = aiosql.from_path("iprefer/item.sql", "sqlite3", record_classes=dict(Item=Item))


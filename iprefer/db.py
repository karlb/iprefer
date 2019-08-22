from dataclasses import dataclass
import sqlite3
import json

import aiosql
from flask import g, url_for

from .iprefer import APP_ROOT

DATABASE = APP_ROOT + '/../data/data.sqlite3'
USER_DATABASE = APP_ROOT + '/../data/user.sqlite3'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.execute(f"ATTACH DATABASE '{USER_DATABASE}' AS user")
    return db


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

    def _make_breadcrumb(self, *keys):
        crumbs = []
        for key in keys:
            value = self.tags.get(key)
            if not value:
                continue
            crumbs.append((value, url_for('.tag', key=key, value=value)))
        return crumbs

    def location_breadcrumb(self):
        return self._make_breadcrumb('addr:country', 'addr:city', 'addr:suburb', "addr:street")

    def amenity_breadcrumb(self):
        return self._make_breadcrumb('amenity', 'cuisine')

    def all_breadcrumbs(self):
        return [
            self.location_breadcrumb(),
            self.amenity_breadcrumb(),
        ]


@dataclass
class User:
    user_id: int
    name: str
    google_id: int


queries = aiosql.from_path(APP_ROOT + "/item.sql", "sqlite3", record_classes=dict(Item=Item))
user_queries = aiosql.from_path(APP_ROOT + "/user.sql", "sqlite3", record_classes=dict(User=User))


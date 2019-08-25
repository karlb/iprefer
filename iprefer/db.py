from dataclasses import dataclass
import sqlite3
import json

import aiosql
from flask import g, url_for

from iprefer import APP_ROOT

DATABASE = APP_ROOT + '/../data/data.sqlite3'
USER_DATABASE = APP_ROOT + '/../data/user.sqlite3'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.execute(f"ATTACH DATABASE '{USER_DATABASE}' AS user")
        db.execute("PRAGMA foreign_keys = ON")
    return db


def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@dataclass
class Item:
    name: str
    item_id: int
    rank: float

    def tag(self, key):
        return queries.tag(g.db, item_id=self.item_id, key=key)

    @property
    def detail(self):
        if g.dataset == 'restaurants':
            values = self.tag('addr:street')
            return values[0] if values else None

    def _make_breadcrumb(self, *keys):
        tags = {
            key: json.loads(values)
            for key, values in queries.tags(g.db, item_id=self.item_id)
        }
        crumbs = []
        for key in keys:
            value = tags.get(key)[0]
            if not value:
                continue
            crumbs.append((value, url_for('.tag', key=key, value=value)))
        return crumbs

    def location_breadcrumb(self):
        return self._make_breadcrumb('addr:country', 'addr:city', 'addr:suburb', "addr:street")

    def amenity_breadcrumb(self):
        return self._make_breadcrumb('amenity', 'cuisine')

    def all_breadcrumbs(self):
        if g.dataset == 'restaurants':
            return [
                self.location_breadcrumb(),
                self.amenity_breadcrumb(),
            ]
        else:
            return []


@dataclass
class User:
    user_id: int
    name: str
    google_id: int


queries = aiosql.from_path(
    APP_ROOT + "/item.sql",
    "sqlite3",
    record_classes=dict(
        Item=Item,
        scalar=lambda value: value,
    )
)
user_queries = aiosql.from_path(APP_ROOT + "/user.sql", "sqlite3", record_classes=dict(User=User))


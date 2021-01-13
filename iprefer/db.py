from dataclasses import dataclass
import sqlite3
import json
from typing import List

import aiosql  # type: ignore
from flask import g, url_for

from iprefer import APP_ROOT
from iprefer.helper import measure_time

USER_DATABASE = APP_ROOT + '/../data/user.sqlite3'


def get_db():
    db = getattr(g, '_user_db', None)
    if db is None:
        db = g._user_db = sqlite3.connect(USER_DATABASE)
        db.execute("PRAGMA foreign_keys = ON")
        if not db.execute(
                "SELECT name from sqlite_master WHERE type='table' AND name='user'"
                ).fetchone():
            with db:
                user_queries.create_schema(db)
    return db


def close_connection(exception):
    db = getattr(g, '_user_db', None)
    if db is not None:
        db.close()


@dataclass
class Item:
    item_id: str
    name: str
    description: str
    alt_names: List[str] 
    lat: float
    lon: float
    rank: float
    importance: float
    tags: dict = '{}'  # type: ignore
    # comparison to main item on page
    is_better: bool = False
    is_worse: bool = False

    def __post_init__(self):
        self.tags = json.loads(self.tags)  # type: ignore
        self.alt_names = json.loads(self.alt_names) if self.alt_names else []  # type: ignore

    @property
    def detail(self):
        if g.dataset['id'] == 'restaurants':
            detail = ' '.join((
                self.tags.get('cuisine', [''])[0].capitalize(),
                self.tags.get('amenity', [''])[0],
            ))
            streets = self.tags.get('addr:street')
            if streets:
                detail += ', ' + streets[0]
            return detail
        if g.dataset['id'] == 'books':
            authors = self.tags.get('author')
            if authors:
                return 'by ' + ', '.join(authors)
            return 'unknown author'
        if g.dataset['id'] == 'software':
            return self.description

    @property
    def image(self):
        if g.dataset['id'] == 'restaurants':
            return url_for('.thumbnail', item_id=self.item_id)
        return None

    def _make_breadcrumb(self, *keys):
        tags = {
            key: json.loads(values)
            for key, values in queries.tags(g.db, item_id=self.item_id)
        }
        crumbs = []
        for key in keys:
            value = tags.get(key, [None])[0]
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


class ProfilingDBAdapter(aiosql.adapters.sqlite3.SQLite3DriverAdapter):

    slow_threshold = 0.1


for method in [
        'select', 'select_one', 'select_value', 'select_cursor',
        'insert_update_delete', 'insert_update_delete_many', 'insert_returning'
    ]:

    def make_wrapped(method):

        def wrapped_func(cls, conn, _query_name, sql, parameters, *args, **kwargs):
            superclass = super(ProfilingDBAdapter, ProfilingDBAdapter)
            with measure_time() as query_duration:
                result = getattr(superclass, method)(
                    conn, _query_name, sql, parameters, *args, **kwargs
                )

            if query_duration > cls.slow_threshold:
                print(f"Query took {query_duration:.2f}s:", _query_name, parameters)

            return result

        return wrapped_func

    setattr(ProfilingDBAdapter, method, classmethod(make_wrapped(method)))


queries = aiosql.from_path(
    APP_ROOT + "/item.sql",
    ProfilingDBAdapter,
    record_classes=dict(
        Item=Item,
        scalar=lambda value: value,
    )
)
user_queries = aiosql.from_path(APP_ROOT + "/user.sql", "sqlite3", record_classes=dict(User=User))


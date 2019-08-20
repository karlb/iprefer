from dataclasses import dataclass
import json

import aiosql
import sqlite3
from flask import Flask, g, render_template

app = Flask(__name__)
DATABASE = 'data/data.sqlite3'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@dataclass
class Item:
    name: str
    id: int
    tags: dict

    def __post_init__(self):
        self.tags = json.loads(self.tags)

    def location_breadcrumb(self):
        return [
            (self.tags['addr:country'], '#'),
            (self.tags['addr:city'], '#'),
            (self.tags['addr:suburb'], '#'),
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


@app.route('/')
def hello_world():
    conn = get_db()
    rows = conn.execute("SELECT * FROM item LIMIT 9")
    items = [Item(*row) for row in rows]
    return render_template('index.html', items=items)


@app.route('/item/<id>')
def item(id):
    conn = get_db()
    main_item = Item(*conn.execute("SELECT * FROM item WHERE id = ?", [id]).fetchone())
    return render_template('item.html', main_item=main_item)

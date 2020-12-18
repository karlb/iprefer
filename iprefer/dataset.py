import os
import sqlite3
import json
import requests

from flask import Flask, g, render_template, jsonify, request, redirect, url_for, session, Blueprint, current_app as app
from flask_dance.contrib.google import make_google_blueprint, google  # type: ignore

from .db import Item, queries, user_queries, USER_DATABASE
from .graph import update_rank


def cached_external_url(url):
    cache_entry = g.cache_db.execute("SELECT data FROM cache WHERE url = ?", [url]).fetchone()
    if cache_entry:
        return cache_entry[0]

    response = requests.get(url)
    if response.status_code == 200:
        data = response.content
        with g.cache_db:
            g.cache_db.execute("INSERT INTO cache(url, data) VALUES (?, ?)", [url, data])
        return data
    else:
        return response.content, response.status_code


def make_blueprint(dataset: dict) -> Blueprint:

    bp = Blueprint('dataset-' + dataset['id'], __name__)

    @bp.before_request
    def open_db():
        g.db = sqlite3.connect(f"{app.instance_path}/{dataset['id']}.sqlite3")
        g.db.execute(f"ATTACH DATABASE '{USER_DATABASE}' AS user")
        g.db.execute("PRAGMA foreign_keys = ON")

        # create cache db
        g.cache_db = sqlite3.connect(f"{app.instance_path}/cache.sqlite3")
        if not g.cache_db.execute('SELECT 1 FROM sqlite_master WHERE name="cache"').fetchone():
            g.cache_db.execute("""
                CREATE TABLE cache(
                    url TEXT PRIMARY KEY,
                    created TIMESTAMP CURRENT_TIMESTAMP,
                    data BLOB NOT NULL
                )
            """)

    @bp.before_request
    def set_dataset():
        g.dataset = dataset

    @bp.route('/')
    def index():
        return render_template('index.html', items=queries.start_page_items(g.db))

    @bp.route('/tag/<key>/<value>')
    def tag(key, value):
        return render_template('index.html', items=queries.tag_items(g.db, key=key, label=value), category=value)

    @bp.route('/search')
    def search():
        return render_template(
            'index.html',
            items=queries.search_items(g.db, term=request.args['term']),
            category='search matches',
        )

    @bp.route('/item/<item_id>', methods=['GET', 'POST'])
    def item(item_id):
        main_item = Item(*g.db.execute("SELECT * FROM item WHERE item_id = ?", [item_id]).fetchone())

        if request.method == 'POST':
            item = Item(*g.db.execute(
                "SELECT * FROM item WHERE item_id = ? LIMIT 1",
                [request.form['item_id']]
            ).fetchone())
            if request.form['better_or_worse'] == 'better':
                preferred = item
                other = main_item
            else:
                preferred = main_item
                other = item
            with g.db:
                queries.save_preference(
                    g.db, user_id=g.user.user_id, prefers=preferred.item_id, to=other.item_id
                )
                update_rank(g.db)

            return redirect(url_for('.item', item_id=item_id))

        tags = {
            key: json.loads(values)
            for key, values in queries.tags(g.db, item_id=item_id)
        }
        ctx = dict(
            main_item=main_item,
            alternatives=queries.alternatives(g.db, item_id=item_id),
            tags=tags,
        )
        if g.get('user'):
            user_id = g.user.user_id
            ctx.update(dict(
                better=queries.better(g.db, user_id=user_id, item_id=item_id),
                worse=queries.worse(g.db, user_id=user_id, item_id=item_id),
            ))

        return render_template('item.html', **ctx)

    @bp.route('/item/<item_id>/remove/<remove_item_id>', methods=['POST'])
    def remove_prefer(item_id, remove_item_id):
        with g.db:
            queries.remove_prefer(g.db, user_id=g.user.user_id, item_id=item_id, remove_item_id=remove_item_id)
        return redirect(url_for('.item', item_id=item_id))

    @bp.route('/item/<item_id>/thumbnail')
    def thumbnail(item_id):
        item = Item(*g.db.execute("SELECT * FROM item WHERE item_id = ?", [item_id]).fetchone())
        if g.dataset['id'] == 'restaurants':
            return cached_external_url(f"https://api.mapbox.com/styles/v1/mapbox/streets-v11/static/pin-s({item.lon},{item.lat})/{item.lon},{item.lat},12/200x120?access_token={g.mapbox_token}")

    @bp.route('/json/typeahead')
    def typeahead():
        items = queries.all_items(g.db)
        return jsonify([
            dict(name=i.name, item_id=i.item_id, detail=i.detail)
            for i in items
        ])

    return bp

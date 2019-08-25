import os
import sqlite3
import json

from flask import Flask, g, render_template, jsonify, request, redirect, url_for, session, Blueprint, current_app as app
from flask_dance.contrib.google import make_google_blueprint, google

from .db import Item, queries, user_queries, USER_DATABASE
from .graph import update_rank


def make_blueprint(dataset: str) -> Blueprint:

    bp = Blueprint('dataset-' + dataset, __name__)

    @bp.before_request
    def open_db():
        g.db = sqlite3.connect(f'{app.instance_path}/{dataset}.sqlite3')
        g.db.execute(f"ATTACH DATABASE '{USER_DATABASE}' AS user")
        g.db.execute("PRAGMA foreign_keys = ON")

    @bp.before_request
    def set_dataset():
        g.dataset = dataset

    @bp.route('/')
    def index():
        return render_template('index.html', items=queries.start_page_items(g.db), category=dataset)

    @bp.route('/tag/<key>/<value>')
    def tag(key, value):
        return render_template('index.html', items=queries.tag_items(g.db, key=key, value=value), category=value)

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
            # TODO: handle name not unique cases
            item = Item(*g.db.execute(
                "SELECT * FROM item WHERE name = ? LIMIT 1",
                [request.form['item_name']]
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

    @bp.route('/json/typeahead')
    def typeahead():
        items = queries.all_items(g.db)
        return jsonify([
            dict(name=i.name, item_id=i.item_id, detail=i.detail)
            for i in items
        ])

    return bp

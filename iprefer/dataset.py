import os

from flask import Flask, g, render_template, jsonify, request, redirect, url_for, session, Blueprint
from flask_dance.contrib.google import make_google_blueprint, google

from .db import get_db, Item, queries, user_queries
from .graph import update_rank


def make_blueprint(dataset: str) -> Blueprint:

    bp = Blueprint('dataset-' + dataset, __name__)

    @bp.route('/')
    def index():
        conn = get_db()
        return render_template('index.html', items=queries.start_page_items(conn), category='Berlin')

    @bp.route('/tag/<key>/<value>')
    def tag(key, value):
        conn = get_db()
        return render_template('index.html', items=queries.tag_items(conn, key=key, value=value), category=value)

    @bp.route('/search')
    def search():
        conn = get_db()
        return render_template(
            'index.html',
            items=queries.search_items(conn, term=request.args['term']),
            category='search matches',
        )

    @bp.route('/item/<item_id>', methods=['GET', 'POST'])
    def item(item_id):
        conn = get_db()
        main_item = Item(*conn.execute("SELECT * FROM item WHERE item_id = ?", [item_id]).fetchone())

        if request.method == 'POST':
            # TODO: handle name not unique cases
            item = Item(*conn.execute(
                "SELECT * FROM item WHERE name = ? LIMIT 1",
                [request.form['item_name']]
            ).fetchone())
            if request.form['better_or_worse'] == 'better':
                preferred = item
                other = main_item
            else:
                preferred = main_item
                other = item
            with conn:
                queries.save_preference(
                    conn, user_id=g.user.user_id, prefers=preferred.item_id, to=other.item_id
                )
                update_rank(conn)

            return redirect(url_for('.item', item_id=item_id))

        ctx = dict(
            main_item=main_item,
            alternatives=queries.alternatives(conn, item_id=item_id),
        )
        if g.get('user'):
            user_id = g.user.user_id
            ctx.update(dict(
                better=queries.better(conn, user_id=user_id, item_id=item_id),
                worse=queries.worse(conn, user_id=user_id, item_id=item_id),
            ))

        return render_template('item.html', **ctx)

    @bp.route('/item/<item_id>/remove/<remove_item_id>', methods=['POST'])
    def remove_prefer(item_id, remove_item_id):
        conn = get_db()
        with conn:
            queries.remove_prefer(conn, user_id=g.user.user_id, item_id=item_id, remove_item_id=remove_item_id)
        return redirect(url_for('.item', item_id=item_id))

    @bp.route('/json/typeahead')
    def typeahead():
        conn = get_db()
        items = queries.all_items(conn)
        return jsonify([
            dict(name=i.name, street=i.tags.get('addr:street'))
            for i in items
        ])

    return bp

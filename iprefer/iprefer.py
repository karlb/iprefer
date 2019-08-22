import os

from flask import Flask, g, render_template, jsonify, request, redirect, url_for, session, Blueprint
from flask_dance.contrib.google import make_google_blueprint, google

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
bp = Blueprint('data', __name__)


from .db import get_db, Item, queries, user_queries
from .graph import update_rank


@bp.before_request
def add_user_to_session():
    if 'user' in session:
        # no need to fetch the user, again
        return
    if not google.authorized:
        # can't fetch the user when not logged in
        return

    try:
        resp = google.get("/oauth2/v1/userinfo")
        assert resp.ok, resp.text
    except Exception:
        del session['user']
        return
    google_user = resp.json()

    conn = get_db()
    user_queries.add_user(
        conn,
        google_id=google_user['id'],
        name=google_user['name'],
    )
    db_user = user_queries.get_user(conn, google_id=google_user['id'])
    print(db_user, '<<<')
    session['user'] = db_user


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
    user_id = session['user'].user_id

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
                conn, user_id=user_id, prefers=preferred.item_id, to=other.item_id
            )
            update_rank(conn)

        return redirect(url_for('.item', item_id=item_id))

    better = queries.better(conn, user_id=user_id, item_id=item_id)
    worse = queries.worse(conn, user_id=user_id, item_id=item_id)
    alternatives = queries.alternatives(conn, item_id=item_id)
    return render_template(
        'item.html',
        main_item=main_item,
        better=better,
        worse=worse,
        alternatives=alternatives,
    )


@bp.route('/json/typeahead')
def typeahead():
    conn = get_db()
    items = queries.all_items(conn)
    return jsonify([
        dict(name=i.name, street=i.tags.get('addr:street'))
        for i in items
    ])

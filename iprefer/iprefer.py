import os

from flask import Flask, g, render_template, jsonify, request, redirect, url_for, session, Blueprint
from flask_dance.contrib.google import make_google_blueprint, google

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
bp = Blueprint('data', __name__)


from .db import get_db, Item, queries, user_queries
from .graph import update_rank


@bp.before_request
def add_user_to_g():
    conn = get_db()
    if 'google_user_id' in session:
        # We know the user, let's just fetch the User object from the db
        g.user = user_queries.get_user(conn, google_id=session['google_user_id'])
        return
    if not google.authorized:
        # Can't fetch the user when not logged in
        return

    try:
        resp = google.get("/oauth2/v1/userinfo")
        assert resp.ok, resp.text
    except Exception as e:
        # Something is wrong with the google authentication. Treat user as logged out.
        print(e)
        return

    # Create new user row from Google account info, if user does not exist, yet.
    google_user = resp.json()
    with conn:
        user_queries.add_user(
            conn,
            google_id=google_user['id'],
            name=google_user['name'],
        )

    session['google_user_id'] = google_user['id']
    g.user = user_queries.get_user(conn, google_id=google_user['id'])


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


@bp.route('/json/typeahead')
def typeahead():
    conn = get_db()
    items = queries.all_items(conn)
    return jsonify([
        dict(name=i.name, street=i.tags.get('addr:street'))
        for i in items
    ])

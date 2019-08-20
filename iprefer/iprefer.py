from flask import Flask, g, render_template, jsonify, request, redirect, url_for

app = Flask(__name__)

from .db import get_db, Item, queries
from .graph import update_rank


@app.route('/')
def index():
    conn = get_db()
    return render_template('index.html', items=queries.start_page_items(conn), category='Berlin')


@app.route('/tag/<key>/<value>')
def tag(key, value):
    conn = get_db()
    return render_template('index.html', items=queries.tag_items(conn, key=key, value=value), category=value)


@app.route('/search')
def search():
    conn = get_db()
    return render_template(
        'index.html',
        items=queries.search_items(conn, term=request.args['term']),
        category='search matches',
    )


@app.route('/item/<item_id>', methods=['GET', 'POST'])
def item(item_id):
    conn = get_db()
    main_item = Item(*conn.execute("SELECT * FROM item WHERE item_id = ?", [item_id]).fetchone())
    user_id = 1

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

        return redirect(url_for('item', item_id=item_id))

    better = queries.better(conn, user_id=user_id, item_id=main_item.item_id)
    worse = queries.worse(conn, user_id=user_id, item_id=main_item.item_id)
    return render_template('item.html', main_item=main_item, better=better, worse=worse)


@app.route('/json/typeahead')
def typeahead():
    conn = get_db()
    items = queries.all_items(conn)
    return jsonify([
        dict(name=i.name, street=i.tags.get('addr:street'))
        for i in items
    ])

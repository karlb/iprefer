import os

from flask import Flask, g, render_template, jsonify, request, redirect, url_for, session, Blueprint
from flask_dance.contrib.google import make_google_blueprint, google

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
    return redirect(url_for('dataset.index'))

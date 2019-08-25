import os

from flask import Flask, session, g
from flask_dance.contrib.google import make_google_blueprint, google

__version__ = '0.1.0'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))


from .iprefer import bp as main_bp
from .db import close_connection, get_db, user_queries
from . import dataset
from .importer import importer_cli


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # db teardown
    app.teardown_appcontext(close_connection)

    # user handling
    app.before_request(add_user_to_g)

    # local blueprints
    app.register_blueprint(main_bp, url_prefix="/")
    for ds in ['restaurants', 'software']:
        app.register_blueprint(dataset.make_blueprint(ds), url_prefix="/" + ds)

    # Google login
    blueprint = make_google_blueprint(
	client_id=app.config.get('GOOGLE_OAUTH_CLIENT_ID'),
	client_secret=app.config.get('GOOGLE_OAUTH_CLIENT_SECRET'),
    )
    app.register_blueprint(blueprint, url_prefix="/login")

    # cli commands for admins
    app.cli.add_command(importer_cli)

    return app


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

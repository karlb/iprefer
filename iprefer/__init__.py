import os

from flask import Flask
from flask_dance.contrib.google import make_google_blueprint, google

__version__ = '0.1.0'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))


from .iprefer import bp as main_bp
from .db import close_connection
from . import dataset


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

    return app

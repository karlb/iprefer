import os

from flask import Flask, g, render_template, jsonify, request, redirect, url_for, session, Blueprint
from flask_dance.contrib.google import make_google_blueprint, google

bp = Blueprint('data', __name__)

from .graph import update_rank


@bp.route('/')
def index():
    return redirect(url_for('dataset-restaurants.index'))

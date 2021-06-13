from .db import Item, queries, user_queries, USER_DATABASE
from flask import Flask, g, render_template, jsonify, request, redirect, url_for, session, Blueprint, current_app as app


def alternatives(item_id, search_term=None):
    ctx = {}
    if hasattr(g, 'user'):
        if search_term:
            ctx['alternatives'] = queries.alternatives_search(g.db, item_id=item_id, search_term=search_term, user_id=g.user.user_id)
        else:
            ctx['alternatives'] = queries.alternatives(g.db, item_id=item_id, user_id=g.user.user_id)
    else:
        ctx['alternatives'] = []

    return render_template('alternatives.html', **ctx)

import xml.etree.ElementTree as ET
import sqlite3
import json
from itertools import chain

import click

from . import importer_cli


def get_osm():
    tree = ET.parse('data/export.osm')
    root = tree.getroot()
    for node in root.iter('node'):
        tags = {
            tag.get('k'): tag.get('v')
            for tag in node.iter('tag')
        }
        if 'name' not in tags:
            continue

        yield dict(
            name=tags.pop('name'),
            id=node.get('id'),
            tags=tags,
            json_tags=json.dumps(tags)
        )


@importer_cli.command('osm')
def import_osm():
    conn = sqlite3.connect('data/data.sqlite3')
    conn.executescript('''
        DROP TABLE IF EXISTS item;
        CREATE TABLE item(
            name text NOT NULL,
            item_id int NOT NULL,
            tags json,
            rank float
        );
        CREATE INDEX rank_idx ON item(rank);

        DROP TABLE IF EXISTS tags;
        CREATE TABLE tags(
            item_id int NOT NULL,
            key text NOT NULL,
            value text NOT NULL,
            PRIMARY KEY (item_id, key)
        );
    ''')
    osm = list(get_osm())
    print(
        conn.executemany(
            'INSERT INTO item(name, item_id, tags) VALUES (:name, :id, :json_tags)',
            osm
        ).rowcount,
        'items inserted'
    )
    print(
        conn.executemany(
            'INSERT INTO tags(item_id, key, value) VALUES (?, ?, ?)',
            chain.from_iterable(
                ((item['id'], key, val) for key, val in item['tags'].items())
                for item in osm
            )
        ).rowcount,
        'tags inserted'
    )
    conn.commit()

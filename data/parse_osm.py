#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import sqlite3
import json

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
            tags=json.dumps(tags)
        )

#for x in get_osm():
#    print(x)

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
''')
print(
    conn.executemany(
        'INSERT INTO item(name, item_id, tags) VALUES (:name, :id, :tags)',
        list(get_osm())
    ).rowcount,
    'rows inserted'
)
conn.commit()

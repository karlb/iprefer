import xml.etree.ElementTree as ET

import click
from flask import current_app as app

from . import importer_cli, save_dataset


def get_osm():
    tree = ET.parse('data/export.osm')
    root = tree.getroot()
    for node in root.iter('node'):
        tags = {
            tag.get('k'): [tag.get('v')]
            for tag in node.iter('tag')
        }
        if 'name' not in tags:
            continue

        yield dict(
            name=tags.pop('name')[0],
            item_id=node.get('id'),
            lat=float(node.get('lat')),
            lon=float(node.get('lon')),
            tags=tags,
        )


@importer_cli.command('osm')
def import_osm():
    filename = app.instance_path + '/restaurants.sqlite3'
    items = list(get_osm())
    save_dataset(filename, items)

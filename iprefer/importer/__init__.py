from flask.cli import AppGroup

importer_cli = AppGroup('import')

from . import osm

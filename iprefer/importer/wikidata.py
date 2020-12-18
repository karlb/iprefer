import sys
from typing import Dict

from SPARQLWrapper import SPARQLWrapper, SPARQLExceptions, JSON  # type: ignore
import click
from flask import current_app as app

from . import importer_cli, save_dataset

ENDPOINT_URL = "https://query.wikidata.org/sparql"
LABEL_SERVICE = 'SERVICE wikibase:label { bd:serviceParam wikibase:language "en,de,fr,es,pt,it,se,no,nl,fi". }'
DATASETS: Dict[str, Dict[str, list]] = {
    "software": {
        "tag_types": [
            # ('isa', 'P31'),
            # ('influenced_by', 'P737'),
            # ('prog_lang', 'P277'),
            # ('use', 'P366'),
            # ('license', 'P275'),
            # ('website', 'P856'),
            # ('feature', 'P751'),
            # ('source_code', 'P1324'),
            ('operating_system', 'P306'),
            # ('developer', 'P178'),
            # ('based_on', 'P144'),
        ],
        "filter": [
            'Q7397',  # software
            'Q9143',  # programming language
            'Q131212',  # text editor (redundant?)
            'Q522972',  # source code editor (redundant?)
        ]
    },
    "books": {
        "tag_types": [
            ('main_subject', 'P921'),
            ('author', 'P50'),
            ('publisher', 'P123'),
        ],
        "filter": [
            'Q571',  # book
            'Q47461344',  # literary work
            'Q277759',  # book series
        ]
    },
}


def get_results(query):
    print(query)
    sparql = SPARQLWrapper(
        ENDPOINT_URL,
        agent='iprefer.to data importer (contact: mail@karl.berlin)',
    )
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        return sparql.query().convert()
    except SPARQLExceptions.EndPointInternalError as e:
        print(e.response)
        sys.exit("SparQL query failed")


def parse_wd_id(binding):
    return binding['value'].replace('http://www.wikidata.org/entity/', '')


def get_items(dataset_name):
    dataset = DATASETS[dataset_name]
    query = """SELECT ?item ?itemLabel
        WHERE
        {
            {
                SELECT DISTINCT ?item
                WHERE {
                    ?item wdt:P31 ?category.
                    VALUES ?category {%(filters)s}.
                }
            }
            %(LABEL_SERVICE)s
        }
    """ % dict(
        filters=' '.join('wd:' + x for x in dataset['filter']),
        LABEL_SERVICE=LABEL_SERVICE,
    )
    item_results = get_results(query)
    dataset = DATASETS[dataset_name]
    items = [
        dict(
            item_id=parse_wd_id(result['item']),
            name=result['itemLabel']['value'],
            lat=None,
            lon=None,
        )
        for result in item_results["results"]["bindings"]
    ]
    return items


def get_items_to_tags(dataset_name):
    dataset = DATASETS[dataset_name]
    filters = ' '.join('wd:' + x for x in dataset['filter'])
    items_to_tags = []
    for tag, predicate in dataset['tag_types']:
        print(f'Fetching tag "{tag}" mappings')
        query = """
            SELECT DISTINCT ?item ?tag
            WHERE {
                ?item wdt:P31 ?category.
                VALUES ?category {%(filters)s}.
                ?item wdt:%(predicate)s ?tag.
            }
        """ % locals()
        tag_results = get_results(query)["results"]["bindings"]
        print(f'{len(tag_results)} results')
        items_to_tags += [
            dict(
                item_id=parse_wd_id(result["item"]),
                tag_id=tag + parse_wd_id(result["tag"]),
            )
            for result in tag_results
        ]

    return items_to_tags


def get_tag_labels(dataset_name):
    dataset = DATASETS[dataset_name]
    items_to_tags = []
    for key, predicate in dataset['tag_types']:
        print(f'Fetching tag "{key}" labels')
        query = """
            SELECT DISTINCT ?tag ?tagLabel
            WHERE {
                ?item wdt:P31 ?category.
                VALUES ?category {%(filters)s}.
                ?item wdt:%(predicate)s ?tag.
                %(LABEL_SERVICE)s
            }
        """ % dict(
            predicate=predicate,
            filters=' '.join('wd:' + x for x in dataset['filter']),
            LABEL_SERVICE=LABEL_SERVICE,
        )
        tag_results = get_results(query)["results"]["bindings"]
        print(f'{len(tag_results)} results')
        items_to_tags += [
            dict(
                tag_id=key + parse_wd_id(result["tag"]),
                key=key,
                label=parse_wd_id(result["tagLabel"]),
            )
            for result in tag_results
        ]

    return items_to_tags


@importer_cli.command('wikidata')
@click.argument('dataset_name', type=click.Choice(DATASETS, case_sensitive=False))
def import_wikidata(dataset_name):
    filename = app.instance_path + '/' + dataset_name + '.sqlite3'

    import sqlite3
    import aiosql  # type: ignore
    from pathlib import Path
    from itertools import chain
    queries = aiosql.from_path(Path(__file__).parent / "dataset.sql", "sqlite3")
    conn = sqlite3.connect(filename)

    queries.create_schema(conn)

    items = get_items(dataset_name)
    print(
        conn.executemany("""
                INSERT INTO item(name, item_id, lat, lon)
                VALUES (:name, :item_id, :lat, :lon)
            """,
            items
        ).rowcount,
        'items inserted'
    )

    items_to_tags = get_items_to_tags(dataset_name)
    print(
        conn.executemany("""
                INSERT INTO item_to_tag(item_id, tag_id)
                VALUES (:item_id, :tag_id)
            """,
            items_to_tags
        ).rowcount,
        'item/tag mappings inserted'
    )

    tags = get_tag_labels(dataset_name)
    print(
        conn.executemany(
            'INSERT INTO tag(tag_id, key, label) VALUES (:tag_id, :key, :label)',
            tags
        ).rowcount,
        'tags inserted'
    )
    conn.commit()

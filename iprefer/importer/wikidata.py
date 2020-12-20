import sys
from typing import Dict, Set
from itertools import islice, chain
import json

from SPARQLWrapper import SPARQLWrapper, SPARQLExceptions, JSON  # type: ignore
import click
from flask import current_app as app

from . import importer_cli, save_dataset
from iprefer.helper import measure_time

ENDPOINT_URL = "https://query.wikidata.org/sparql"
LABEL_SERVICE = 'SERVICE wikibase:label { bd:serviceParam wikibase:language "en,de,fr,es,pt,it,se,no,nl,fi". }'
DATASETS: Dict[str, Dict[str, list]] = {
    "software": {
        "tag_types": [
            ('isa', 'P31'),
            ('influenced_by', 'P737'),
            ('prog_lang', 'P277'),
            ('use', 'P366'),
            ('license', 'P275'),
            ('website', 'P856'),
            ('feature', 'P751'),
            ('source_code', 'P1324'),
            ('operating_system', 'P306'),
            ('developer', 'P178'),
            ('based_on', 'P144'),
        ],
        "filter": [
            'Q7397',  # software
            'Q9143',  # programming language
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
            'Q7725634',  # literary work
            'Q277759',  # book series
        ]
    },
}


class TimeoutException(Exception):
    pass


def get_results(query):
    print(query)
    sparql = SPARQLWrapper(
        ENDPOINT_URL,
        agent='iprefer.to data importer (contact: mail@karl.berlin)',
    )
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        query_result = sparql.query()
        # debug_filename = app.instance_path + '/bad_response.json'
        # with open(debug_filename, 'wb') as f:
        #     f.write(query_result.response.read())
        #     print('Bad response written to', debug_filename)
        #     raise Exception('Stopped to examine response')
        return query_result.convert()
    except SPARQLExceptions.EndPointInternalError as e:
        if 'TimeoutException' in e.args[0]:
            raise TimeoutException
        print(e.args[0])
        sys.exit("SparQL query failed")
    except json.decoder.JSONDecodeError:
        print('JSON decoding failed, assuming timeout while returning JSON')
        raise TimeoutException



def parse_wd_id(binding):
    return binding['value'].replace('http://www.wikidata.org/entity/', '')


def get_item_classes(dataset_name):
    cache_filename = app.instance_path + '/' + dataset_name + '_classes_cache.txt'
    try:
        with open(cache_filename) as f:
            classes = f.read().split(' ')
    except FileNotFoundError:
        dataset = DATASETS[dataset_name]
        query = """
            SELECT ?class
            WHERE {
                VALUES ?category {%(filters)s}.
                ?class wdt:P279* ?category.
            }
        """ % dict(
            filters=' '.join('wd:' + x for x in dataset['filter']),
        )
        class_results = get_results(query)
        classes = [
            parse_wd_id(result['class'])
            for result in class_results["results"]["bindings"]
        ]

        with open(cache_filename, 'w') as f:
            f.write(' '.join(classes))

    return classes


def parse_single_result(result_row: dict):
    return tuple(
        parse_wd_id(field) if field['type'] == 'uri' else field['value']
        for field in result_row.values()
    )


def batch_query(query, item_classes, batch_size=100):
    iterator = iter(item_classes)
    results: Set[tuple] = set()
    while True:
        batch = list(islice(iterator, batch_size))
        if not batch:
            return results

        prepared_query = query.replace(
            'CLASSES',
            ' '.join('wd:' + x for x in batch),
        )
        try:
            with measure_time() as query_duration:
                batch_results = get_results(prepared_query)["results"]["bindings"]
        except TimeoutException:
            # Put elements from failed batch back into the iterator and retry
            # with a smaller batch size.
            iterator = chain(batch, iterator)
            batch_size //= 2
            print(f'Query timeout. Reduced batch size to {batch_size}.')
            continue

        print(f'{len(batch_results)} results')
        results |= {
            parse_single_result(result)
            for result in batch_results
        }
        if query_duration < 5:
            batch_size += 1
        if query_duration > 30:
            batch_size //= 2
    return results


def get_items(item_classes):
    query = """SELECT DISTINCT ?item ?itemLabel
        WHERE
        {
            {
                SELECT ?item ?itemLabel
                WHERE {
                    ?item wdt:P31 ?class.
                    VALUES ?class {CLASSES}.
                    %(LABEL_SERVICE)s
                }
            }
            FILTER lang(?itemLabel)  # filter out elements without label
        }
    """ % dict(
        LABEL_SERVICE=LABEL_SERVICE,
    )
    result_tuples = batch_query(query, item_classes)
    yield from (
        dict(
            item_id=result[0],
            name=result[1],
            lat=None,
            lon=None,
        )
        for result in result_tuples
    )


def get_items_to_tags(dataset, item_classes):
    for tag, predicate in dataset['tag_types']:
        print(f'Fetching tag "{tag}" mappings')
        query = """
            SELECT DISTINCT ?item ?tag
            WHERE {
                VALUES ?class {CLASSES}.
                ?item wdt:P31 ?class.
                ?item wdt:%(predicate)s ?tag.
            }
        """ % dict(
            predicate=predicate,
        )
        result_tuples = batch_query(query, item_classes)
        yield from (
            dict(
                item_id=result[0],
                tag_id=tag + result[1],
            )
            for result in result_tuples
        )


def get_tag_labels(dataset, item_classes):
    for key, predicate in dataset['tag_types']:
        print(f'Fetching tag "{key}" labels')
        query = """
            SELECT DISTINCT ?tag ?tagLabel
            WHERE {
                VALUES ?class {CLASSES}.
                ?item wdt:P31 ?class.
                ?item wdt:%(predicate)s ?tag.
                %(LABEL_SERVICE)s
            }
        """ % dict(
            predicate=predicate,
            LABEL_SERVICE=LABEL_SERVICE,
        )
        result_tuples = batch_query(query, item_classes, batch_size=50)
        yield from (
            dict(
                tag_id=key + result[0],
                key=key,
                label=result[1],
            )
            for result in result_tuples
        )


@importer_cli.command('wikidata')
@click.argument('dataset_name', type=click.Choice(DATASETS, case_sensitive=False))
def import_wikidata(dataset_name):
    filename = app.instance_path + '/' + dataset_name + '.sqlite3'

    import sqlite3
    import aiosql  # type: ignore
    from pathlib import Path
    queries = aiosql.from_path(Path(__file__).parent / "dataset.sql", "sqlite3")
    conn = sqlite3.connect(filename)

    queries.create_schema(conn)
    item_classes = get_item_classes(dataset_name)
    dataset = DATASETS[dataset_name]

    items = get_items(item_classes)
    print(
        conn.executemany("""
                INSERT INTO item(name, item_id, lat, lon)
                VALUES (:name, :item_id, :lat, :lon)
            """,
            items
        ).rowcount,
        'items inserted'
    )
    conn.commit()

    tags = get_tag_labels(dataset, item_classes)
    print(
        conn.executemany(
            'INSERT INTO tag(tag_id, key, label) VALUES (:tag_id, :key, :label)',
            tags
        ).rowcount,
        'tags inserted'
    )
    conn.commit()

    items_to_tags = get_items_to_tags(dataset, item_classes)
    print(
        conn.executemany("""
                INSERT INTO item_to_tag(item_id, tag_id)
                VALUES (:item_id, :tag_id)
            """,
            items_to_tags
        ).rowcount,
        'item/tag mappings inserted'
    )
    conn.commit()

    queries.refresh_views(conn)
    conn.execute('ANALYZE')
    conn.commit()

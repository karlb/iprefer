import sys

from SPARQLWrapper import SPARQLWrapper, SPARQLExceptions, JSON
import click
from flask import current_app as app

from . import importer_cli, save_dataset

ENDPOINT_URL = "https://query.wikidata.org/sparql"
LIST_SEP = '|||'
DATASETS = {
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
            # ('main_subject', 'P921'),
            # ('author', 'P50'),
            # ('publisher', 'P123'),
        ],
        "filter": [
            'Q571',  # book
            'Q47461344',  # literary work
        ]
    },
}

def make_query(dataset_name):
    dataset = DATASETS[dataset_name]
    select_list = ' '.join('?' + tag + 's' for tag, _ in dataset['tag_types'])
    join_list = '\n'.join("""
          OPTIONAL {
            SELECT ?item
                   (GROUP_CONCAT(DISTINCT ?%(tag)sLabel;separator="%(list_sep)s") AS ?%(tag)ss)
            WHERE {
              ?item wdt:%(predicate)s ?%(tag)s.
              ?%(tag)s rdfs:label ?%(tag)sLabel. FILTER( LANG(?%(tag)sLabel)="en" )
            }
            GROUP BY ?item
          }
        """ % dict(tag=tag, predicate=predicate, list_sep=LIST_SEP)
        for tag, predicate in dataset['tag_types']
    )
    filters = ' '.join('wd:' + x for x in dataset['filter'])
    query = """SELECT ?item ?itemLabel %(select_list)s

    WITH {
        SELECT DISTINCT ?item
        WHERE {                 
          ?item wdt:P31 ?category.
          # VALUES ?item {wd:Q305876}
          VALUES ?category {%(filters)s}.
        }
    } AS %%items

    WHERE 
    {
        INCLUDE %%items
        %(join_list)s
        ?item rdfs:label ?itemLabel. FILTER( LANG(?itemLabel)="en" )
    }
    """ % locals()

    return query


def get_results(endpoint_url, query):
    print(query)
    sparql = SPARQLWrapper(
        endpoint_url,
        agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
    )
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        return sparql.query().convert()
    except SPARQLExceptions.EndPointInternalError as e:
        print(e.response)
        sys.exit("SparQL query failed")



def get_wikidata(dataset_name):
    query = make_query(dataset_name)
    results = get_results(ENDPOINT_URL, query)
    dataset = DATASETS[dataset_name]
    items = [
        dict(
            item_id=result['item']['value'].replace('http://www.wikidata.org/entity/', ''),
            name=result['itemLabel']['value'],
            lat=None,
            lon=None,
            tags={
                tag: result[tag + 's']['value'].split(LIST_SEP)
                for tag, _ in dataset['tag_types']
                if tag + 's' in result
            },
        )
        for result in results["results"]["bindings"]
    ]
    return items

@importer_cli.command('wikidata')
@click.argument('dataset_name', type=click.Choice(DATASETS, case_sensitive=False))
def import_wikidata(dataset_name):
    filename = app.instance_path + '/' + dataset_name + '.sqlite3'
    items = list(get_wikidata(dataset_name))
    save_dataset(filename, items)

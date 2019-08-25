from SPARQLWrapper import SPARQLWrapper, JSON
import click
from flask import current_app as app

from . import importer_cli, save_dataset

endpoint_url = "https://query.wikidata.org/sparql"

list_sep = '|||'
tag_types = [
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
]
select_list = ' '.join('?' + tag + 's' for tag, _ in tag_types)
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
    """ % dict(tag=tag, predicate=predicate, list_sep=list_sep)
    for tag, predicate in tag_types
)
query = """SELECT ?item ?itemLabel %(select_list)s

WITH {
    SELECT DISTINCT ?item
    WHERE {                 
      ?item wdt:P31 ?software.
      # VALUES ?item {wd:Q305876}
      VALUES ?software {wd:Q7397 wd:Q9143 wd:Q131212 wd:Q522972}.
    }
} AS %%items

WHERE 
{
    INCLUDE %%items
    %(join_list)s
    ?item rdfs:label ?itemLabel. FILTER( LANG(?itemLabel)="en" )
}
""" % locals()


def get_results(endpoint_url, query):
    print(query)
    sparql = SPARQLWrapper(
        endpoint_url,
        agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
    )
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()

def get_wikidata():
    results = get_results(endpoint_url, query)
    items = [
        dict(
            item_id=result['item']['value'].replace('http://www.wikidata.org/entity/', ''),
            name=result['itemLabel']['value'],
            tags={
                tag: result[tag + 's']['value'].split(list_sep)
                for tag, _ in tag_types
                if tag + 's' in result
            },
        )
        for result in results["results"]["bindings"]
    ]
    return items

@importer_cli.command('wikidata')
def import_wikidata():
    filename = app.instance_path + '/software.sqlite3'
    items = list(get_wikidata())
    save_dataset(filename, items)

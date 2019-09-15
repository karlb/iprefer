from typing import Tuple, Iterable, List
from pprint import pprint

import networkx as nx

from iprefer.db import queries
from iprefer.graph import load_graph, calc_rank


def rank_items(conn, preferences: Iterable[Tuple[int, str, str]], expected: List[str]):
    """ Ranking from point of view of user 1 """
    for user, prefers, to in preferences:
        queries.save_preference(
            conn, user_id=user, prefers=prefers, to=to
        )
    G = load_graph(conn)
    ranking = calc_rank(G)
    sorted_items = [
        item
        for _, item in sorted((rank, item) for item, rank in ranking.items())
    ]
    try:
        assert sorted_items == expected
        assert len(ranking.values()) == len(set(ranking.values())), 'Ambigous ranking'
    except AssertionError:
        nx.drawing.nx_agraph.write_dot(G, 'failed_graph.dot')
        pprint(ranking)
        print('The graph that did not yield the expected order is saved to `failed_graph.dot`.')
        raise


def test_ranking_basic(conn):
    rank_items(conn, [
        # user, prefers, to
        (1, 'A', 'B'),
        (1, 'B', 'C'),
    ], ['A', 'B', 'C'])


def test_ranking_branched(conn):
    rank_items(conn, [
        (1, 'A', 'B'),
        (1, 'A', 'C'),
        (1, 'B', 'C'),
        (1, 'B', 'D'),
        (1, 'C', 'D'),
    ], ['A', 'B', 'C', 'D'])


def test_ranking_quantity(conn):
    """ Two preferences are more important than a single one """
    rank_items(conn, [
        (2, 'A', 'B'),
        (3, 'A', 'B'),
        (4, 'B', 'A'),
    ], [ 'A', 'B'])


# def test_ranking_user_pref(conn):
#     rank_items(conn, [
#         (1, 'A', 'B'),
#         (2, 'B', 'A'),
#         (3, 'B', 'A'),
#     ], [ 'A', 'B'])

from typing import Dict

import networkx as nx

from .db import queries


Ranking = Dict[str, float]


def load_graph(conn) -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_weighted_edges_from(queries.get_graph(conn))
    return G


def calc_rank(G: nx.DiGraph) -> Ranking:
    return nx.pagerank(G)


def save_rank(conn, rank: Ranking):
    queries.save_rank(
        conn,
        (
            dict(item_id=node, rank=rank)
            for node, rank in pagerank.items()
        )
    )


def update_rank(conn):
    G = load_graph(conn)
    pagerank = calc_rank(G)
    save_rank(conn, G)

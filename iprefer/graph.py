import networkx as nx

from .db import queries

def update_rank(conn):
    G = nx.DiGraph()
    G.add_edges_from(queries.get_graph(conn))
    pagerank = nx.pagerank(G)
    queries.save_rank(
        conn,
        (
            dict(item_id=node, rank=rank)
            for node, rank in pagerank.items()
        )
    )

    # Debugging:
    # nx.drawing.nx_agraph.write_dot(G, 'graph.dot')

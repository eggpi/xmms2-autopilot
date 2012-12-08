import networkx
import random
import logging

_graph = None

MAX_OUT_DEGREE = 10
MAX_IN_DEGREE = 5

GRAPH_DOT_FILE = "autopilot_graph.dot"
GRAPH_PERSISTENCE_FILE = "autopilot_graph.pickle"

def _ensure_graph(f):
    def decorated_f(*args, **kwds):
        global _graph
        if _graph is None:
            try:
                _graph = networkx.read_gpickle(GRAPH_PERSISTENCE_FILE)
                logging.info("successfully loaded graph from %s",
                             GRAPH_PERSISTENCE_FILE)
            except:
                _graph = networkx.DiGraph()
                logging.info("starting with an empty graph")

        return f(*args, **kwds)

    return decorated_f

def _dump_graph(f):
    @_ensure_graph
    def decorated_f(*args, **kwds):
        ret = f(*args, **kwds)
        networkx.write_dot(_graph, GRAPH_DOT_FILE)
        networkx.write_gpickle(_graph, GRAPH_PERSISTENCE_FILE)
        return ret

    return decorated_f

def _get_min_weight_neighbor(u, in_or_out):
    """
    Get the in- or out-neighbor that is connected to a vertex with a least-cost
    edge.
    """

    if in_or_out == "out":
        neighbors = _graph.sucessors(u)
    else:
        neighbors = _graph.predecessors(u)

    min_neighbor = None
    for un in neighbors:
        weight = graph[u][un]["weight"]
        if min_neighbor is None or weight < min_neighbor[1]:
            min_neighbor = (un, weight)

    return min_neighbor[0]

@_dump_graph
def positive(u, v):
    """
    Give a positive feedback from node u to node v.
    """

    if _graph.has_edge(u, v):
        _graph[u][v]["weight"] += 1.0
    else:
        if u in _graph and _graph.out_degree(u) == MAX_OUT_DEGREE:
            _graph.remove_edge(u, _get_min_weight_neighbor(u), "out")
        if v in _graph and _graph.in_degree(v) == MAX_IN_DEGREE:
            _graph.remove_edge(u, _get_min_weight_neighbor(v), "in")

        _graph.add_edge(u, v, weight = 1.0)

    logging.debug("%s -(%s)> %s", u, _graph[u][v]["weight"], v)

@_dump_graph
def negative(u, v):
    """
    Give a negative feedback from node u to node v.
    """

    if _graph.has_edge(u, v):
        _graph[u][v]["weight"] -= 1.0

        if _graph[u][v]["weight"] == 0:
            _graph.remove_edge(u, v)
            logging.debug("deleted edge %s -> %s", u, v)
        else:
            logging.debug("%s -(%s)> %s", u, _graph[u][v]["weight"], v)
    else:
        logging.debug("%s -> %s doesn't exist, doing nothing", u, v)

@_dump_graph
def _compute_candidates(u, k):
    """
    Compute the candidate nodes starting at u.

    The candidate nodes are those at distance < k from u, in
    number of edges.

    Returns a dictionary mapping candidates to their weights
    """

    candidates = {}
    distances = {u: 0.0}
    for parent, child in networkx.bfs_edges(_graph, u):
        distances[child] = distances[parent] + 1.0
        if distances[child] > k:
            break

        candidates[child] = _graph[parent][child]["weight"] / distances[child]

    if len(_graph) > len(candidates) + 1:
        # pick one extra random node
        random_node = random.choice(_graph.nodes())
        while random_node in candidates or random_node == u:
            random_node = random.choice(_graph.nodes())

        if candidates:
            candidates[random_node] = min(candidates.values())
        else:
            candidates[random_node] = 1.0

    return candidates

@_dump_graph
def next(u, k = 3):
    """
    Pick a next node, starting at node u.
    """

    if u not in _graph:
        _graph.add_node(u)

    candidates = _compute_candidates(u, k)
    if not candidates:
        return None

    sum_weights = float(sum(candidates.values()))

    probabilities = {}
    for c in candidates:
        probabilities[c] = candidates[c] / sum_weights

    candidates = candidates.keys()

    intervals = [probabilities[c] for c in candidates]
    intervals = list(networkx.utils.cumulative_sum(intervals))

    r = random.random()
    for i, p in enumerate(intervals):
        if r < p:
            return candidates[i]

    assert False

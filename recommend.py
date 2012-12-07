import networkx
import random

_graph = None

MAX_DEGREE = 10

def _ensure_graph(f):
    def decorated_f(*args, **kwds):
        global _graph
        if _graph is None:
            _graph = networkx.DiGraph()

        return f(*args, **kwds)

    return decorated_f

def _get_min_weight_neighbor(u):
    """
    Get the neighbor that is connected to a vertex with a least-cost
    edge.
    """

    min_neighbor = None
    for un in _graph.neighbors(u):
        weight = graph[u][un]["weight"]
        if min_neighbor is None or weight < min_neighbor[1]:
            min_neighbor = (un, weight)

    return min_neighbor[0]

@_ensure_graph
def positive(u, v):
    """
    Give a positive feedback from node u to node v.
    """

    if _graph.has_edge(u, v):
        _graph[u][v]["weight"] += 1.0
    else:
        if _graph.out_degree(u) == MAX_DEGREE:
            _graph.remove_edge(u, _get_min_weight_neighbor(u))
        _graph.add_edge(u, v, weight = 1.0)

@_ensure_graph
def negative(u, v):
    """
    Give a negative feedback from node u to node v.
    """

    if _graph.has_edge(u, v):
        _graph.remove_edge(u, v)

@_ensure_graph
def _compute_candidates(u, k):
    """
    Compute the candidate nodes starting at u.

    The candidate nodes are those at distance < k from u, in
    number of edges.

    Returns a dictionary mapping candidates to their weights
    """

    candidates = {}
    distances = {u: 0}
    for parent, child in networkx.bfs_edges(_graph, u):
        distances[child] = distances[parent] + 1
        if distances[child] > k:
            break

        candidates[child] = _graph[parent][child]["weight"]

    return candidates

@_ensure_graph
def next(u, k = 3):
    """
    Pick a next node, starting at node u.
    """

    candidates = _compute_candidates(u, k)
    sum_weights = sum(candidates.values())

    probabilities = {}
    for c in candidates:
        probabilities[c] = candidates[c] / float(sum_weights)

    candidates = candidates.keys()

    intervals = [probabilities[c] for c in candidates]
    intervals = [sum(intervals[:i]) for i in range(len(intervals))]
    intervals.append(1)

    r = random.random()

    for i, p in enumerate(intervals[1:]):
        if r < p:
            positive(u, candidates[i])
            return candidates[i]

    assert False

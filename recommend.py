import networkx
import random
import logging
import functools

_graph = None

MIN_CANDIDATES = 3
MIN_GRAPH_SIZE = 20
MAX_OUT_DEGREE = 10
MAX_IN_DEGREE = 5

GRAPH_DOT_FILE = None
GRAPH_PERSISTENCE_FILE = None

def _ensure_graph(f):
    @functools.wraps(f)
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
    @functools.wraps(f)
    def decorated_f(*args, **kwds):
        ret = f(*args, **kwds)

        if GRAPH_DOT_FILE is not None:
            try:
                networkx.write_dot(_graph, GRAPH_DOT_FILE)
            except:
                logging.warning("failed to save dot file '%s'",
                                GRAPH_DOT_FILE)

        if GRAPH_PERSISTENCE_FILE is not None:
            try:
                networkx.write_gpickle(_graph, GRAPH_PERSISTENCE_FILE)
            except:
                logging.warning("failed to save graph file '%s'",
                                GRAPH_PERSISTENCE_FILE)
        return ret

    return decorated_f

_get_neighbor_edges = \
    lambda u, in_or_out: \
        ((v, d) for u, v, d in _graph.out_edges(u, True)) \
        if in_or_out == "out" else \
        ((v, d) for v, u, d in _graph.in_edges(u, True))

_get_min_weight_neighbor = \
    lambda u, in_or_out: \
        min((d["weight"], v)
            for v, d in _get_neighbor_edges(u, in_or_out))[1]

_get_max_weight_neighbor = \
    lambda u, in_or_out: \
        max((d["weight"], v)
            for v, d in _get_neighbor_edges(u, in_or_out))[1]

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
def _compute_candidates(u, k, climb = True):
    """
    Compute the candidate nodes starting at u.

    The candidate nodes are those at distance < k from u, in
    number of edges.

    Returns a dictionary mapping candidates to their weights
    """

    # find candidates among successors
    candidates = {}
    distances = {u: 0.0}
    for parent, child in networkx.bfs_edges(_graph, u):
        distances[child] = distances[parent] + 1.0
        if distances[child] > k:
            break

        candidates[child] = _graph[parent][child]["weight"] / distances[child]

    if len(candidates) < MIN_CANDIDATES-1 and climb:
        logging.debug("not enough candidates for %s, try climbing", u)
        # union with candidates from predecessor with greatest weight
        try:
            pred = _get_max_weight_neighbor(u, "in")
        except ValueError:
            pred = None

        if pred is not None:
            more_candidates = _compute_candidates(pred, k, climb = False)
            logging.debug("climbing %s yields %s", pred, more_candidates)
            more_candidates.pop(u, None) # don't use our node itself
            more_candidates.update(candidates) # use weights from 'candidates'

            candidates = more_candidates

    # pick one extra random node
    if len(_graph) > len(candidates) + 1:
        random_node = random.choice(_graph.nodes())
        while random_node in candidates or random_node == u:
            random_node = random.choice(_graph.nodes())

        if candidates:
            candidates[random_node] = min(candidates.values())
        else:
            candidates[random_node] = 1.0

        logging.debug("picked random candidate %s with weight %s",
                      random_node, candidates[random_node])

    return candidates

def _weighted_random_pick(pool):
    """
    Randomly pick an element from a pool of weighted candidates.

    The pool parameter should be a dictionary mapping elements to weights.
    """

    sum_weights = sum(pool.values())

    candidates = pool.keys()
    probabilities = [pool[c] / sum_weights for c in candidates]
    intervals = networkx.utils.cumulative_sum(probabilities)

    r = random.random()
    for c, i in zip(candidates, intervals):
        if r < i:
            return c

    assert False

@_dump_graph
def next(u, k = 3, default = None):
    """
    Pick a next node, starting at node u.
    """

    if u not in _graph:
        _graph.add_node(u)

    if len(_graph) < MIN_GRAPH_SIZE:
        logging.debug("small graph, returning the default")
        return default

    candidates = _compute_candidates(u, k)
    if len(candidates) < MIN_CANDIDATES:
        logging.debug("not enough candidates, returning the default")
        return default

    logging.debug("candidates for %s: %s", u, candidates)
    return _weighted_random_pick(candidates)

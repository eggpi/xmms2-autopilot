import recommend

import random
import unittest

def fresh_random(mth):
    def decorated_mth(*args, **kwds):
        random.seed("random seed")
        return mth(*args, **kwds)
    return decorated_mth

class TestRecommend(unittest.TestCase):
    def setUp(self):
        import networkx

        g = networkx.DiGraph()

        g.add_edge(1, 2, weight = 2)
        g.add_edge(2, 1, weight = 1)
        g.add_edge(1, 3, weight = 3)
        g.add_edge(3, 4, weight = 1)
        g.add_edge(3, 5, weight = 1)
        g.add_edge(3, 6, weight = 2)
        g.add_edge(6, 2, weight = 1)
        g.add_edge(2, 7, weight = 1)
        g.add_edge(7, 8, weight = 1)
        g.add_edge(7, 9, weight = 1)
        g.add_edge(7, 10, weight = 1)
        g.add_edge(10, 11, weight = 1)

        recommend._graph = g
        recommend.MIN_GRAPH_SIZE = 0
        recommend.MIN_CANDIDATES = 0
        recommend.GRAPH_DOT_FILE = None
        recommend.GRAPH_PERSISTENCE_FILE = None

    def test_get_min_weight_neighbor(self):
        self.assertEquals(recommend._get_min_weight_neighbor(2, "in"), 6)
        self.assertEquals(recommend._get_min_weight_neighbor(5, "in"), 3)
        self.assertEquals(recommend._get_min_weight_neighbor(6, "out"), 2)
        self.assertEquals(recommend._get_min_weight_neighbor(3, "out"), 4)
        self.assertRaises(ValueError, recommend._get_min_weight_neighbor, 9, "out")

    def test_get_max_weight_neighbor(self):
        self.assertEquals(recommend._get_max_weight_neighbor(1, "in"), 2)
        self.assertEquals(recommend._get_max_weight_neighbor(3, "in"), 1)
        self.assertEquals(recommend._get_max_weight_neighbor(6, "out"), 2)
        self.assertEquals(recommend._get_max_weight_neighbor(1, "out"), 3)
        self.assertRaises(ValueError, recommend._get_max_weight_neighbor, 9, "out")

    @fresh_random
    def test_compute_candidates(self):
        # no climbing, last item is the random choice
        self.assertEquals(recommend._compute_candidates(1, 1), {2: 2.0, 3: 3.0, 4: 2.0})
        self.assertEquals(recommend._compute_candidates(1, 2), {2: 2.0, 3: 3.0, 4: 0.5, 5: 0.5, 6: 1.0, 7: 0.5, 8: 0.5})
        self.assertEquals(recommend._compute_candidates(1, 3), {2: 2.0, 3: 3.0, 4: 0.5, 5: 0.5, 6: 1.0, 7: 0.5, 8: 1.0 / 3, 9: 1.0 / 3, 10: 1.0 / 3, 11: 1.0 / 3})
        self.assertEquals(recommend._compute_candidates(6, 1), {2: 1.0, 8: 1.0})
        self.assertEquals(recommend._compute_candidates(6, 2), {1: 0.5, 2: 1.0, 7: 0.5, 11: 0.5})

        # exercise climbing, last two items are the random choices for the
        # parent and the node
        min_candidates, recommend.MIN_CANDIDATES = recommend.MIN_CANDIDATES, 3
        self.assertEquals(recommend._compute_candidates(5, 1), {4: 1.0, 6: 2.0, 7: 1.0, 11: 1.0})
        self.assertEquals(recommend._compute_candidates(11, 2), {3: 1.0, 7: 1.0})
        recommend.MIN_CANDIDATES = min_candidates

    @fresh_random
    def test_next(self):
        self.assertEquals(recommend.next(1, 2), 3)
        self.assertEquals(recommend.next(20), 11)

    @fresh_random
    def test_min_candidates(self):
        min_candidates, recommend.MIN_CANDIDATES = recommend.MIN_CANDIDATES, float("inf")
        self.assertEquals(recommend.next(10, 3), None)
        recommend.MIN_CANDIDATES = 0
        self.assertEquals(recommend.next(10, 3), 11)
        recommend.MIN_CANDIDATES = min_candidates

if __name__ == "__main__":
    unittest.main()

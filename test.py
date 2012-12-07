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

    @fresh_random
    def test_compute_candidates(self):
        io = [
            ((1, 1), {2: 2.0, 3: 3.0, 4: 1.0}),
            ((1, 2), {2: 2.0, 3: 3.0, 4: 0.5, 5: 0.5, 6: 1.0, 7: 0.5, 8: 1.0}),
            ((1, 3), {2: 2.0, 3: 3.0, 4: 0.5, 5: 0.5, 6: 1.0, 7: 0.5, 8: 1.0 / 3, 9: 1.0 / 3, 10: 1.0 / 3, 11: 1.0}),
            ((6, 1), {2: 1.0, 8: 1.0}),
            ((6, 2), {1: 0.5, 2: 1.0, 7: 0.5, 11: 1.0})
        ]

        for input, output in io:
            self.assertEquals(output, recommend._compute_candidates(*input))

    @fresh_random
    def test_next(self):
        self.assertEquals(recommend.next(1, 2), 3)
        self.assertEquals(recommend.next(20), None)

if __name__ == "__main__":
    unittest.main()

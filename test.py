import unittest
import recommend

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

    def test_compute_candidates(self):
        io = [
            ((1, 1), {2: 2, 3: 3}),
            ((1, 2), {2: 2, 3: 3, 4: 1, 5: 1, 6: 2, 7: 1}),
            ((1, 3), {2: 2, 3: 3, 4: 1, 5: 1, 6: 2, 7: 1, 8: 1, 9: 1, 10: 1}),
            ((6, 1), {2: 1}),
            ((6, 2), {1: 1, 2: 1, 7: 1})
        ]

        for input, output in io:
            self.assertEquals(recommend._compute_candidates(*input), output)

    def test_next(self):
        n = recommend.next(1, 1)
        self.assertIn(n, (2, 3))

if __name__ == "__main__":
    unittest.main()

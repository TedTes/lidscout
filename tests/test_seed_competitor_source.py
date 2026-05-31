import unittest


@unittest.skip("seed_competitor_source worker uses removed Postgres repos — needs rewrite")
class SeedCompetitorSourceTests(unittest.TestCase):
    def test_placeholder(self):
        pass


if __name__ == "__main__":
    unittest.main()

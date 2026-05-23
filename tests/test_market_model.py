import unittest

from domain.market import Market


class MarketModelTests(unittest.TestCase):
    def test_creates_market_with_normalized_fields(self):
        market = Market.create(
            id=" workspace-tools ",
            name=" Workspace tools ",
            description=" Tools for async teams ",
            target_user=" product teams ",
            idea_prompt=" find collaboration pain ",
        )

        self.assertEqual(market.id, "workspace-tools")
        self.assertEqual(market.name, "Workspace tools")
        self.assertEqual(market.description, "Tools for async teams")
        self.assertEqual(market.target_user, "product teams")
        self.assertEqual(market.idea_prompt, "find collaboration pain")
        self.assertIsNotNone(market.created_at)

    def test_rejects_blank_required_fields(self):
        with self.assertRaises(ValueError):
            Market.create(id="", name="Workspace tools")
        with self.assertRaises(ValueError):
            Market.create(id="workspace-tools", name=" ")


if __name__ == "__main__":
    unittest.main()

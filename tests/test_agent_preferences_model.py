import unittest

from domain.agent import AgentFeedback, AgentPreferences


class AgentPreferencesModelTests(unittest.TestCase):
    def test_creates_clean_preferences(self):
        preferences = AgentPreferences.create(
            market_id=" devtools ",
            preferred_source_families=["social", " social ", "reviews"],
            ignored_themes=["pricing", ""],
            extra_instructions=" prioritize enterprise pain ",
        )

        self.assertEqual(preferences.market_id, "devtools")
        self.assertEqual(preferences.preferred_source_families, ["social", "reviews"])
        self.assertEqual(preferences.ignored_themes, ["pricing"])
        self.assertEqual(preferences.extra_instructions, "prioritize enterprise pain")
        self.assertIsNotNone(preferences.created_at)
        self.assertIsNotNone(preferences.updated_at)

    def test_rejects_missing_market_id(self):
        with self.assertRaises(ValueError):
            AgentPreferences.create(market_id=" ")

    def test_creates_feedback(self):
        feedback = AgentFeedback.create(
            id="feedback-1",
            market_id=" devtools ",
            opportunity_id=" opportunity-1 ",
            action="SAVE",
            reason=" Strong evidence ",
        )

        self.assertEqual(feedback.id, "feedback-1")
        self.assertEqual(feedback.market_id, "devtools")
        self.assertEqual(feedback.opportunity_id, "opportunity-1")
        self.assertEqual(feedback.action, "save")
        self.assertEqual(feedback.reason, "Strong evidence")

    def test_rejects_unsupported_feedback_action(self):
        with self.assertRaises(ValueError):
            AgentFeedback.create(
                market_id="devtools",
                opportunity_id="opportunity-1",
                action="archive",
            )


if __name__ == "__main__":
    unittest.main()

import unittest

from domain.agent import AgentActivity, AgentFeedback, AgentPreferences


class AgentPreferencesModelTests(unittest.TestCase):
    def test_creates_clean_preferences(self):
        preferences = AgentPreferences.create(
            user_niche_id=" devtools ",
            preferred_source_families=["social", " social ", "reviews"],
            ignored_themes=["pricing", ""],
            extra_instructions=" prioritize enterprise pain ",
        )

        self.assertEqual(preferences.user_niche_id, "devtools")
        self.assertEqual(preferences.preferred_source_families, ["social", "reviews"])
        self.assertEqual(preferences.ignored_themes, ["pricing"])
        self.assertEqual(preferences.extra_instructions, "prioritize enterprise pain")
        self.assertIsNotNone(preferences.created_at)
        self.assertIsNotNone(preferences.updated_at)

    def test_rejects_missing_user_niche_id(self):
        with self.assertRaises(ValueError):
            AgentPreferences.create(user_niche_id=" ")

    def test_creates_feedback(self):
        feedback = AgentFeedback.create(
            id="feedback-1",
            user_niche_id=" devtools ",
            opportunity_id=" opportunity-1 ",
            action="SAVE",
            reason=" Strong evidence ",
        )

        self.assertEqual(feedback.id, "feedback-1")
        self.assertEqual(feedback.user_niche_id, "devtools")
        self.assertEqual(feedback.opportunity_id, "opportunity-1")
        self.assertEqual(feedback.action, "save")
        self.assertEqual(feedback.reason, "Strong evidence")

    def test_rejects_unsupported_feedback_action(self):
        with self.assertRaises(ValueError):
            AgentFeedback.create(
                user_niche_id="devtools",
                opportunity_id="opportunity-1",
                action="archive",
            )

    def test_creates_activity(self):
        activity = AgentActivity.create(
            id="activity-1",
            user_niche_id=" devtools ",
            event_type="RUN_COMPLETED",
            title=" Scan finished ",
            detail=" Found one gap. ",
            metadata={"fetched_count": 10},
        )

        self.assertEqual(activity.id, "activity-1")
        self.assertEqual(activity.user_niche_id, "devtools")
        self.assertEqual(activity.event_type, "run_completed")
        self.assertEqual(activity.title, "Scan finished")
        self.assertEqual(activity.detail, "Found one gap.")
        self.assertEqual(activity.metadata["fetched_count"], 10)

    def test_rejects_unsupported_activity_type(self):
        with self.assertRaises(ValueError):
            AgentActivity.create(
                user_niche_id="devtools",
                event_type="unknown",
                title="Unknown event",
            )


if __name__ == "__main__":
    unittest.main()

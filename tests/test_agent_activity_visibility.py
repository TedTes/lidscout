import unittest

from api.routes.signals import _user_visible_agent_activity
from domain.agent import AgentActivity


class AgentActivityVisibilityTests(unittest.TestCase):
    def test_hides_post_level_diagnostics_from_user_activity(self):
        activity = [
            AgentActivity.create(
                user_niche_id="market-1",
                event_type="run_completed",
                title="Agent scan completed",
            ),
            AgentActivity.create(
                user_niche_id="market-1",
                event_type="post_filtered",
                title="Filtered: unrelated post",
            ),
            AgentActivity.create(
                user_niche_id="market-1",
                event_type="post_evaluating",
                title="Evaluating: unrelated post",
            ),
            AgentActivity.create(
                user_niche_id="market-1",
                event_type="posts_filtered",
                title="Filtered 21 irrelevant posts",
            ),
        ]

        visible = _user_visible_agent_activity(activity)

        self.assertEqual(
            [item.event_type for item in visible],
            ["run_completed", "posts_filtered"],
        )


if __name__ == "__main__":
    unittest.main()

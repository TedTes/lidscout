import unittest

from application.extraction import RuleBasedRelevanceFilter
from domain.post import RawPost


class RuleBasedRelevanceFilterTests(unittest.TestCase):
    def setUp(self):
        self.filter = RuleBasedRelevanceFilter()

    def test_accepts_competitor_complaint(self):
        result = self.filter.evaluate(
            self._post(
                title="Acme CRM exports keep failing",
                body="The CSV export is broken and finance teams need a workaround.",
                competitor_name="Acme CRM",
                competitor_domain="acme.example",
            )
        )

        self.assertTrue(result.is_relevant)
        self.assertTrue(result.is_about_competitor)
        self.assertTrue(result.has_pain_or_request)
        self.assertIsNone(result.rejection_category)

    def test_rejects_missing_competitor_context(self):
        result = self.filter.evaluate(
            self._post(
                title="Rows is much cheaper than SyncBank",
                body="Users can save money by switching finance tools.",
                competitor_name="Notion",
                competitor_domain="notion.so",
            )
        )

        self.assertFalse(result.is_relevant)
        self.assertEqual(result.rejection_category, "wrong_subject")

    def test_rejects_tutorial_content(self):
        result = self.filter.evaluate(
            self._post(
                title="Acme CRM tutorial",
                body="A step by step guide for creating a sales dashboard.",
                competitor_name="Acme CRM",
            )
        )

        self.assertFalse(result.is_relevant)
        self.assertEqual(result.rejection_category, "tutorial_or_template")

    def test_rejects_job_posting(self):
        result = self.filter.evaluate(
            self._post(
                title="Acme CRM is hiring",
                body="We are hiring for a product manager. Apply now.",
                competitor_name="Acme CRM",
            )
        )

        self.assertFalse(result.is_relevant)
        self.assertEqual(result.rejection_category, "job_posting")

    def test_accepts_uncertain_posts_for_llm_review(self):
        result = self.filter.evaluate(
            self._post(
                title="Acme CRM and enterprise accounts",
                body="Teams keep talking about export workflows in large accounts.",
                competitor_name="Acme CRM",
            )
        )

        self.assertTrue(result.is_relevant)
        self.assertTrue(result.is_about_competitor)
        self.assertFalse(result.has_pain_or_request)

    def test_rejects_empty_content(self):
        result = self.filter.evaluate(
            self._post(title="", body="", competitor_name="Acme CRM")
        )

        self.assertFalse(result.is_relevant)
        self.assertEqual(result.rejection_category, "empty")

    def _post(
        self,
        *,
        title: str,
        body: str,
        competitor_name: str | None = None,
        competitor_domain: str | None = None,
    ) -> RawPost:
        metadata = {"competitor_id": "acme"}
        if competitor_name:
            metadata["competitor_name"] = competitor_name
        if competitor_domain:
            metadata["competitor_domain"] = competitor_domain
        return RawPost.create(
            source="web",
            source_id=title or "empty",
            title=title,
            body=body,
            url="https://example.com/source",
            metadata=metadata,
        )


if __name__ == "__main__":
    unittest.main()

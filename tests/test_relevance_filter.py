import unittest

from application.extraction import LLMRelevanceFilter, RuleBasedRelevanceFilter
from domain.post import RawPost
from infrastructure.llm import MockLLMClient


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


class LLMRelevanceFilterTests(unittest.TestCase):
    def test_accepts_structured_llm_relevance_result(self):
        llm_client = MockLLMClient(
            """
            {
              "is_relevant": true,
              "is_about_competitor": true,
              "has_pain_or_request": true,
              "rejection_category": null,
              "reason": "The post complains about Acme CRM exports.",
              "confidence": 0.88
            }
            """
        )

        result = LLMRelevanceFilter(llm_client).evaluate(
            self._post(
                title="Acme CRM exports fail",
                body="The export feature is broken for finance teams.",
                competitor_name="Acme CRM",
            )
        )

        self.assertTrue(result.is_relevant)
        self.assertTrue(result.is_about_competitor)
        self.assertTrue(result.has_pain_or_request)
        self.assertEqual(result.confidence, 0.88)
        self.assertIsNone(result.rejection_category)
        self.assertIn("learned negative feedback", llm_client.calls[0][0])
        self.assertIn("agent_extra_instructions", llm_client.calls[0][0])
        self.assertIn("competitor_name: Acme CRM", llm_client.calls[0][1])

    def test_rejects_wrong_subject_llm_relevance_result(self):
        llm_client = MockLLMClient(
            """
            {
              "is_relevant": false,
              "is_about_competitor": false,
              "has_pain_or_request": true,
              "rejection_category": "wrong_subject",
              "reason": "The complaint is about another product.",
              "confidence": 0.92
            }
            """
        )

        result = LLMRelevanceFilter(llm_client).evaluate(
            self._post(
                title="Rows is cheaper than SyncBank",
                body="Users can save money with another tool.",
                competitor_name="Notion",
            )
        )

        self.assertFalse(result.is_relevant)
        self.assertEqual(result.rejection_category, "wrong_subject")
        self.assertTrue(result.has_pain_or_request)

    def test_rejects_invalid_llm_relevance_json(self):
        with self.assertRaises(ValueError):
            LLMRelevanceFilter(MockLLMClient("not-json")).evaluate(
                self._post(
                    title="Acme CRM exports fail",
                    body="Exports are broken.",
                    competitor_name="Acme CRM",
                )
            )

    def _post(
        self,
        *,
        title: str,
        body: str,
        competitor_name: str | None = None,
    ) -> RawPost:
        metadata = {"competitor_id": "acme"}
        if competitor_name:
            metadata["competitor_name"] = competitor_name
        return RawPost.create(
            source="web",
            source_id=title,
            title=title,
            body=body,
            url="https://example.com/source",
            metadata=metadata,
        )


if __name__ == "__main__":
    unittest.main()

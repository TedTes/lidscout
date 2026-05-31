import json
import unittest
from unittest.mock import MagicMock

from application.opportunity import OpportunitySynthesisService
from domain.cluster import SignalCluster
from domain.signal import Signal
from infrastructure.db import InMemoryOpportunityRepository


class OpportunitySynthesisServiceTests(unittest.TestCase):
    def test_synthesizes_and_persists_opportunities_from_high_score_clusters(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
        )
        signal = Signal.create(
            id="signal-1",
            post_id="post-1",
            pain="Reporting setup takes too long.",
            user_type="finance teams",
            job_to_be_done="close month-end reporting",
            current_workaround="exporting spreadsheets",
            urgency="high",
            severity="high",
            willingness_to_pay=True,
            category="Reporting",
            confidence=0.9,
        )
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Reporting",
            summary="Teams struggle to configure useful reports.",
            signal_ids=["signal-1"],
            frequency=1,
            average_score=8.4,
            top_examples=["Reporting setup takes too long."],
        )

        result = service.synthesize([cluster], [signal])

        self.assertEqual(result.synthesized_count, 1)
        self.assertEqual(result.inserted_count, 1)
        self.assertEqual(result.failed_count, 0)
        opportunity = result.opportunities[0]
        self.assertEqual(opportunity.id, "opportunity-cluster-1")
        self.assertEqual(opportunity.cluster_id, "cluster-1")
        self.assertEqual(
            opportunity.title,
            "Reduce reporting friction for finance teams",
        )
        self.assertEqual(opportunity.target_user, "finance teams")
        self.assertIn("average opportunity score of 8.4", opportunity.why_it_matters)
        self.assertIn("exporting spreadsheets", opportunity.suggested_wedge)
        self.assertEqual(opportunity.evidence_count, 1)
        self.assertEqual(opportunity.evidence_signal_ids, ["signal-1"])
        self.assertEqual(repository.get_opportunity("opportunity-cluster-1"), opportunity)

    def test_skips_clusters_below_score_threshold(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
        )
        signal = Signal.create(
            id="signal-1",
            post_id="post-1",
            pain="Minor reporting annoyance.",
        )
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Reporting",
            summary="Minor reporting annoyance.",
            signal_ids=["signal-1"],
            frequency=1,
            average_score=4.0,
        )

        result = service.synthesize([cluster], [signal])

        self.assertEqual(result.synthesized_count, 0)
        self.assertEqual(result.inserted_count, 0)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(repository.list_opportunities(), [])

    def test_counts_cluster_without_matching_signal_as_failed(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=0.0,
        )
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Reporting",
            summary="Teams struggle to configure useful reports.",
            signal_ids=["missing-signal"],
            frequency=1,
            average_score=8.4,
        )

        result = service.synthesize([cluster], [])

        self.assertEqual(result.synthesized_count, 0)
        self.assertEqual(result.inserted_count, 0)
        self.assertEqual(result.failed_count, 1)


    def _make_cluster_and_signal(self):
        signal = Signal.create(
            id="signal-1",
            post_id="post-1",
            pain="Reporting setup takes too long.",
            user_type="finance teams",
            job_to_be_done="close month-end reporting",
            current_workaround="exporting spreadsheets",
            urgency="high",
            severity="high",
            willingness_to_pay=True,
            category="Reporting",
            confidence=0.9,
        )
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Reporting",
            summary="Teams struggle to configure useful reports.",
            signal_ids=["signal-1"],
            frequency=3,
            average_score=8.4,
            top_examples=["Reporting setup takes too long."],
        )
        return cluster, signal

    def test_uses_llm_when_client_provided(self):
        repository = InMemoryOpportunityRepository()
        llm_response = {
            "title": "Streamline month-end reporting for finance teams",
            "target_user": "finance teams",
            "pain_summary": "Month-end close is blocked by slow report configuration.",
            "why_it_matters": "Finance teams lose hours each cycle to manual workarounds.",
            "suggested_wedge": "Pre-built report templates that eliminate spreadsheet exports.",
        }
        llm_client = MagicMock()
        llm_client.generate_structured_response.return_value = json.dumps(llm_response)

        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
            llm_client=llm_client,
        )
        cluster, signal = self._make_cluster_and_signal()
        result = service.synthesize([cluster], [signal])

        self.assertEqual(result.synthesized_count, 1)
        opportunity = result.opportunities[0]
        self.assertEqual(opportunity.title, llm_response["title"])
        self.assertEqual(opportunity.target_user, llm_response["target_user"])
        self.assertEqual(opportunity.pain_summary, llm_response["pain_summary"])
        self.assertEqual(opportunity.why_it_matters, llm_response["why_it_matters"])
        self.assertEqual(opportunity.suggested_wedge, llm_response["suggested_wedge"])
        llm_client.generate_structured_response.assert_called_once()

    def test_llm_synthesis_receives_grounded_evidence_context(self):
        repository = InMemoryOpportunityRepository()
        llm_client = MagicMock()
        llm_client.generate_structured_response.return_value = json.dumps(
            {
                "title": "Make workspace calendars reliable across timezones",
                "target_user": "operations teams",
                "pain_summary": "Teams lose trust when calendar sync fails.",
                "why_it_matters": "The evidence exposes a reliability gap in daily planning.",
                "suggested_wedge": "Build a conflict-aware calendar sync layer.",
            }
        )
        signals = [
            Signal.create(
                id="signal-1",
                post_id="reddit:r1",
                pain="Calendar sync fails across timezones.",
                user_type="operations teams",
                job_to_be_done="coordinate weekly planning",
                current_workaround="falling back to Google Calendar",
                urgency="high",
                severity="high",
                willingness_to_pay=True,
                category="Calendar reliability",
                confidence=0.9,
                niche_company_id="notion",
                niche_id="workspace-tools",
                evidence_text="Timezone sync made Notion Calendar unusable.",
                evidence_url="https://reddit.com/r/Notion/comments/1",
            ),
            Signal.create(
                id="signal-2",
                post_id="g2:notion-1",
                pain="Calendar events disappear for shared workspaces.",
                user_type="operations teams",
                job_to_be_done="coordinate weekly planning",
                current_workaround="manual calendar checks",
                urgency="medium",
                severity="high",
                willingness_to_pay=None,
                category="Calendar reliability",
                confidence=0.8,
                niche_company_id="notion",
                niche_id="workspace-tools",
                evidence_text="Shared events disappear without warning.",
                evidence_url="https://g2.com/products/notion/reviews/1",
            ),
        ]
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Calendar reliability",
            summary="Teams cannot trust calendar sync.",
            signal_ids=["signal-1", "signal-2"],
            frequency=2,
            average_score=8.6,
            top_examples=["Calendar sync fails across timezones."],
        )
        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
            llm_client=llm_client,
        )

        result = service.synthesize([cluster], signals)

        self.assertEqual(result.synthesized_count, 1)
        _, content, _ = llm_client.generate_structured_response.call_args.args
        self.assertIn("source_diversity: 2", content)
        self.assertIn("market_ids: workspace-tools", content)
        self.assertIn("competitor_ids: notion", content)
        self.assertIn("evidence_text: Timezone sync made Notion Calendar unusable.", content)
        self.assertIn("evidence_url: https://reddit.com/r/Notion/comments/1", content)
        self.assertIn("job_to_be_done: coordinate weekly planning", content)

    def test_confidence_uses_evidence_count_source_diversity_and_signal_confidence(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(repository, minimum_average_score=0.0)
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Calendar reliability",
            summary="Teams cannot trust calendar sync.",
            signal_ids=["signal-1", "signal-2"],
            frequency=2,
            average_score=8.0,
        )
        shared_kwargs = {
            "post_id": "reddit:r1",
            "pain": "Calendar sync fails.",
            "confidence": 0.9,
        }
        low_diversity_signals = [
            Signal.create(
                id="signal-1",
                evidence_url="https://reddit.com/r/Notion/comments/1",
                **shared_kwargs,
            ),
            Signal.create(
                id="signal-2",
                evidence_url="https://reddit.com/r/Notion/comments/2",
                **shared_kwargs,
            ),
        ]
        high_diversity_signals = [
            Signal.create(
                id="signal-1",
                evidence_url="https://reddit.com/r/Notion/comments/1",
                **shared_kwargs,
            ),
            Signal.create(
                id="signal-2",
                evidence_url="https://g2.com/products/notion/reviews/1",
                **shared_kwargs,
            ),
        ]

        low_diversity = service.synthesize([cluster], low_diversity_signals).opportunities[0]
        high_diversity = service.synthesize([cluster], high_diversity_signals).opportunities[0]

        self.assertGreater(high_diversity.confidence, low_diversity.confidence)

    def test_falls_back_to_templates_when_llm_raises(self):
        repository = InMemoryOpportunityRepository()
        llm_client = MagicMock()
        llm_client.generate_structured_response.side_effect = RuntimeError("API timeout")

        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
            llm_client=llm_client,
        )
        cluster, signal = self._make_cluster_and_signal()
        result = service.synthesize([cluster], [signal])

        self.assertEqual(result.synthesized_count, 1)
        self.assertEqual(result.failed_count, 0)
        opportunity = result.opportunities[0]
        self.assertIn("Reduce", opportunity.title)

    def test_falls_back_to_templates_when_llm_returns_invalid_json(self):
        repository = InMemoryOpportunityRepository()
        llm_client = MagicMock()
        llm_client.generate_structured_response.return_value = "not json {"

        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
            llm_client=llm_client,
        )
        cluster, signal = self._make_cluster_and_signal()
        result = service.synthesize([cluster], [signal])

        self.assertEqual(result.synthesized_count, 1)
        self.assertEqual(result.failed_count, 0)
        opportunity = result.opportunities[0]
        self.assertIn("Reduce", opportunity.title)

    def test_falls_back_to_templates_when_llm_returns_empty_field(self):
        repository = InMemoryOpportunityRepository()
        llm_response = {
            "title": "",
            "target_user": "finance teams",
            "pain_summary": "Some pain.",
            "why_it_matters": "It matters.",
            "suggested_wedge": "Build something.",
        }
        llm_client = MagicMock()
        llm_client.generate_structured_response.return_value = json.dumps(llm_response)

        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
            llm_client=llm_client,
        )
        cluster, signal = self._make_cluster_and_signal()
        result = service.synthesize([cluster], [signal])

        self.assertEqual(result.synthesized_count, 1)
        opportunity = result.opportunities[0]
        self.assertNotEqual(opportunity.title, "")


if __name__ == "__main__":
    unittest.main()

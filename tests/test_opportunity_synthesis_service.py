import json
import unittest
from unittest.mock import MagicMock

from application.opportunity import OpportunitySynthesisService
from domain.cluster import SignalCluster
from domain.signal import Signal
from infrastructure.db import InMemoryOpportunityRepository


class OpportunitySynthesisServiceTests(unittest.TestCase):
    def test_synthesizes_and_persists_opportunities_from_qualified_clusters(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
        )
        cluster, signals = self._make_qualifying_cluster_and_signals()

        result = service.synthesize([cluster], signals)

        self.assertEqual(result.synthesized_count, 1)
        self.assertEqual(result.inserted_count, 1)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(result.rejected_qualifications, [])
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
        self.assertEqual(opportunity.evidence_count, 2)
        self.assertEqual(opportunity.evidence_signal_ids, ["signal-1", "signal-2"])
        self.assertEqual(opportunity.unmet_need_type, "time")
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

    def test_rejects_single_evidence_clusters(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(repository, minimum_average_score=0.0)
        signal = Signal.create(
            id="signal-1",
            post_id="g2:shipstation-1",
            pain="Shipping sync fails during fulfillment.",
            urgency="high",
            severity="high",
            confidence=0.95,
            evidence_url="https://example.com/review/1",
            niche_company_id="shipstation",
        )
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Shipping reliability",
            summary="Operators report unreliable shipping sync.",
            signal_ids=["signal-1"],
            frequency=1,
            average_score=9.5,
        )

        result = service.synthesize([cluster], [signal])

        self.assertEqual(result.synthesized_count, 0)
        self.assertEqual(result.rejected_qualifications[0].reason, "insufficient_evidence")

    def test_rejects_single_vendor_clusters_without_cross_tool_pattern(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(repository, minimum_average_score=0.0)
        signals = [
            Signal.create(
                id="signal-1",
                post_id="reddit:1",
                pain="Calendar sync fails across timezones.",
                user_type="operations teams",
                urgency="high",
                severity="high",
                confidence=0.9,
                niche_company_id="notion",
                evidence_url="https://reddit.com/r/Notion/comments/1",
            ),
            Signal.create(
                id="signal-2",
                post_id="g2:1",
                pain="Calendar events disappear for shared workspaces.",
                user_type="operations teams",
                urgency="high",
                severity="high",
                confidence=0.86,
                niche_company_id="notion",
                evidence_url="https://g2.com/products/notion/reviews/1",
            ),
        ]
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Calendar reliability",
            summary="Teams cannot trust Notion calendar sync.",
            signal_ids=["signal-1", "signal-2"],
            frequency=2,
            average_score=8.6,
        )

        result = service.synthesize([cluster], signals)

        self.assertEqual(result.synthesized_count, 0)
        self.assertEqual(result.rejected_qualifications[0].reason, "no_cross_tool_pattern")

    def test_rejects_thin_clusters_from_weak_only_sources(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(repository, minimum_average_score=0.0)
        signals = [
            Signal.create(
                id="signal-1",
                post_id="blog:1",
                pain="Teams need faster billing reconciliation.",
                niche_company_id="acme-billing",
                evidence_url="https://example.com/blog/billing-tools",
            ),
            Signal.create(
                id="signal-2",
                post_id="blog:2",
                pain="Billing reconciliation is still manual.",
                niche_company_id="northstar-billing",
                evidence_url="https://another-example.com/posts/reconciliation",
            ),
        ]
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Billing reconciliation",
            summary="Teams still reconcile billing manually.",
            signal_ids=["signal-1", "signal-2"],
            frequency=2,
            average_score=8.6,
        )

        result = service.synthesize([cluster], signals)

        self.assertEqual(result.synthesized_count, 0)
        self.assertEqual(result.rejected_qualifications[0].reason, "weak_source_mix")
        self.assertEqual(result.rejected_qualifications[0].high_signal_source_count, 0)

    def test_rejects_vendor_fix_only_clusters(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(repository, minimum_average_score=0.0)
        signals = [
            Signal.create(
                id="signal-1",
                post_id="reddit:1",
                pain="Default page titles are broken and need a setting to customize titles.",
                user_type="site operators",
                urgency="high",
                severity="high",
                confidence=0.9,
                niche_company_id="sitebuilder",
                evidence_url="https://reddit.com/r/sitebuilder/comments/1",
            ),
            Signal.create(
                id="signal-2",
                post_id="forum:1",
                pain="Users want the vendor to fix the default title bug.",
                user_type="site operators",
                urgency="high",
                severity="high",
                confidence=0.86,
                niche_company_id="sitebuilder",
                evidence_url="https://forum.example.com/t/1",
            ),
        ]
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Default page title bug",
            summary="One vendor's page title defaults are broken.",
            signal_ids=["signal-1", "signal-2"],
            frequency=2,
            average_score=8.6,
        )

        result = service.synthesize([cluster], signals)

        self.assertEqual(result.synthesized_count, 0)
        self.assertEqual(result.rejected_qualifications[0].reason, "vendor_fix_only")

    def test_rejects_low_confidence_clusters(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(repository, minimum_average_score=0.0)
        signals = [
            self._signal(
                "signal-1",
                company="shipstation",
                url="https://reddit.com/r/ecommerce/comments/1",
                confidence=0.42,
            ),
            self._signal(
                "signal-2",
                company="shipblink",
                url="https://g2.com/products/shipblink/reviews/1",
                confidence=0.51,
            ),
        ]
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Shipping reliability",
            summary="Operators report shipping reliability pain.",
            signal_ids=["signal-1", "signal-2"],
            frequency=2,
            average_score=8.6,
        )

        result = service.synthesize([cluster], signals)

        self.assertEqual(result.synthesized_count, 0)
        qualification = result.rejected_qualifications[0]
        self.assertEqual(qualification.reason, "low_extraction_confidence")
        self.assertLess(qualification.average_signal_confidence, 0.55)

    def test_rejects_clusters_without_buyer_context(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(repository, minimum_average_score=0.0)
        signals = [
            Signal.create(
                id="signal-1",
                post_id="reddit:1",
                pain="Shipping sync fails during fulfillment.",
                urgency="high",
                severity="high",
                confidence=0.9,
                niche_company_id="shipstation",
                evidence_url="https://reddit.com/r/ecommerce/comments/1",
            ),
            Signal.create(
                id="signal-2",
                post_id="g2:1",
                pain="Fulfillment sync breaks during peak order volume.",
                urgency="high",
                severity="high",
                confidence=0.88,
                niche_company_id="shipblink",
                evidence_url="https://g2.com/products/shipblink/reviews/1",
            ),
        ]
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Shipping reliability",
            summary="Operators report shipping reliability pain.",
            signal_ids=["signal-1", "signal-2"],
            frequency=2,
            average_score=8.6,
        )

        result = service.synthesize([cluster], signals)

        self.assertEqual(result.synthesized_count, 0)
        self.assertEqual(result.rejected_qualifications[0].reason, "thin_buyer_context")

    def test_rejects_low_intensity_clusters(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(repository, minimum_average_score=0.0)
        signals = [
            self._signal(
                "signal-1",
                company="shipstation",
                url="https://reddit.com/r/ecommerce/comments/1",
                urgency="low",
                severity="low",
            ),
            self._signal(
                "signal-2",
                company="shipblink",
                url="https://g2.com/products/shipblink/reviews/1",
                urgency="low",
                severity="low",
            ),
        ]
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Shipping reliability",
            summary="Operators mention shipping reliability.",
            signal_ids=["signal-1", "signal-2"],
            frequency=2,
            average_score=8.6,
        )

        result = service.synthesize([cluster], signals)

        self.assertEqual(result.synthesized_count, 0)
        self.assertEqual(result.rejected_qualifications[0].reason, "low_pain_intensity")

    def test_uses_llm_when_client_provided(self):
        repository = InMemoryOpportunityRepository()
        llm_response = {
            "title": "Streamline month-end reporting for finance teams",
            "target_user": "finance teams",
            "pain_summary": "Month-end close is blocked by slow report configuration.",
            "why_it_matters": "Finance teams lose hours each cycle to manual workarounds.",
            "suggested_wedge": "Pre-built report templates that eliminate spreadsheet exports.",
            "unmet_need_type": "time",
        }
        llm_client = MagicMock()
        llm_client.generate_structured_response.return_value = json.dumps(llm_response)

        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
            llm_client=llm_client,
        )
        cluster, signals = self._make_qualifying_cluster_and_signals()
        result = service.synthesize([cluster], signals)

        self.assertEqual(result.synthesized_count, 1)
        opportunity = result.opportunities[0]
        self.assertEqual(opportunity.title, llm_response["title"])
        self.assertEqual(opportunity.target_user, llm_response["target_user"])
        self.assertEqual(opportunity.pain_summary, llm_response["pain_summary"])
        self.assertEqual(opportunity.why_it_matters, llm_response["why_it_matters"])
        self.assertEqual(opportunity.suggested_wedge, llm_response["suggested_wedge"])
        self.assertEqual(opportunity.unmet_need_type, "time")
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
                "unmet_need_type": "capability",
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
                post_id="g2:coda-1",
                pain="Calendar events disappear for shared workspaces.",
                user_type="operations teams",
                job_to_be_done="coordinate weekly planning",
                current_workaround="manual calendar checks",
                urgency="medium",
                severity="high",
                willingness_to_pay=None,
                category="Calendar reliability",
                confidence=0.8,
                niche_company_id="coda",
                niche_id="workspace-tools",
                evidence_text="Shared events disappear without warning.",
                evidence_url="https://g2.com/products/coda/reviews/1",
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
        self.assertIn("notion", content)
        self.assertIn("coda", content)
        self.assertIn("evidence_text: Timezone sync made Notion Calendar unusable.", content)
        self.assertIn("evidence_url: https://reddit.com/r/Notion/comments/1", content)
        self.assertIn("job_to_be_done: coordinate weekly planning", content)

    def test_confidence_uses_evidence_count_source_diversity_and_signal_confidence(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(repository, minimum_average_score=0.0)
        low_cluster = SignalCluster.create(
            id="cluster-low",
            theme="Calendar reliability",
            summary="Teams cannot trust calendar sync.",
            signal_ids=["signal-1", "signal-2"],
            frequency=2,
            average_score=8.0,
        )
        high_cluster = SignalCluster.create(
            id="cluster-high",
            theme="Calendar reliability",
            summary="Teams cannot trust calendar sync.",
            signal_ids=["signal-1", "signal-2", "signal-3"],
            frequency=3,
            average_score=8.0,
        )
        low_diversity_signals = [
            self._signal("signal-1", company="notion", url="https://reddit.com/r/Notion/comments/1"),
            self._signal("signal-2", company="coda", url="https://g2.com/products/coda/reviews/1"),
        ]
        high_diversity_signals = [
            *low_diversity_signals,
            self._signal("signal-3", company="coda", url="https://news.ycombinator.com/item?id=1"),
        ]

        low_diversity = service.synthesize([low_cluster], low_diversity_signals).opportunities[0]
        high_diversity = service.synthesize([high_cluster], high_diversity_signals).opportunities[0]

        self.assertGreater(high_diversity.confidence, low_diversity.confidence)

    def test_merges_near_duplicate_opportunity_cards(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(repository, minimum_average_score=0.0)
        signals = [
            self._signal(
                "signal-1",
                company="shipstation",
                url="https://reddit.com/r/ecommerce/comments/1",
                pain="Ecommerce operators need reliable shipping sync.",
                category="Shipping integration",
            ),
            self._signal(
                "signal-2",
                company="shipblink",
                url="https://g2.com/products/shipblink/reviews/1",
                pain="Fulfillment teams need reliable shipping sync.",
                category="Shipping integration",
            ),
            self._signal(
                "signal-3",
                company="shipstation",
                url="https://news.ycombinator.com/item?id=1",
                pain="Shipping reliability pushes operators toward alternatives.",
                category="Shipping software",
            ),
            self._signal(
                "signal-4",
                company="shipblink",
                url="https://reddit.com/r/shopify/comments/2",
                pain="Shipping reliability pushes ecommerce teams toward alternatives.",
                category="Shipping software",
            ),
        ]
        clusters = [
            SignalCluster.create(
                id="cluster-1",
                theme="Shipping integration",
                summary="Ecommerce operators need more reliable fulfillment sync.",
                signal_ids=["signal-1", "signal-2"],
                frequency=2,
                average_score=8.0,
            ),
            SignalCluster.create(
                id="cluster-2",
                theme="Shipping software",
                summary="Shipping reliability pushes ecommerce operators to alternatives.",
                signal_ids=["signal-3", "signal-4"],
                frequency=2,
                average_score=8.0,
            ),
        ]

        result = service.synthesize(clusters, signals)

        self.assertEqual(result.synthesized_count, 1)
        self.assertEqual(result.opportunities[0].evidence_count, 4)
        self.assertEqual(
            result.opportunities[0].evidence_signal_ids,
            ["signal-1", "signal-2", "signal-3", "signal-4"],
        )

    def test_falls_back_to_templates_when_llm_raises(self):
        repository = InMemoryOpportunityRepository()
        llm_client = MagicMock()
        llm_client.generate_structured_response.side_effect = RuntimeError("API timeout")

        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
            llm_client=llm_client,
        )
        cluster, signals = self._make_qualifying_cluster_and_signals()
        result = service.synthesize([cluster], signals)

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
        cluster, signals = self._make_qualifying_cluster_and_signals()
        result = service.synthesize([cluster], signals)

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
            "unmet_need_type": "effort",
        }
        llm_client = MagicMock()
        llm_client.generate_structured_response.return_value = json.dumps(llm_response)

        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
            llm_client=llm_client,
        )
        cluster, signals = self._make_qualifying_cluster_and_signals()
        result = service.synthesize([cluster], signals)

        self.assertEqual(result.synthesized_count, 1)
        opportunity = result.opportunities[0]
        self.assertNotEqual(opportunity.title, "")

    def _make_qualifying_cluster_and_signals(self):
        signals = [
            Signal.create(
                id="signal-1",
                post_id="reddit:r1",
                pain="Reporting setup takes too long.",
                user_type="finance teams",
                job_to_be_done="close month-end reporting",
                current_workaround="exporting spreadsheets",
                urgency="high",
                severity="high",
                willingness_to_pay=True,
                category="Reporting",
                confidence=0.9,
                niche_company_id="acme-reports",
                evidence_url="https://reddit.com/r/finance/comments/1",
            ),
            Signal.create(
                id="signal-2",
                post_id="g2:1",
                pain="Dashboard exports take hours before finance can close reporting.",
                user_type="finance teams",
                job_to_be_done="close month-end reporting",
                current_workaround="exporting spreadsheets",
                urgency="high",
                severity="high",
                willingness_to_pay=True,
                category="Reporting",
                confidence=0.86,
                niche_company_id="northstar-bi",
                evidence_url="https://g2.com/products/northstar/reviews/1",
            ),
        ]
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Reporting",
            summary="Teams struggle to configure useful reports.",
            signal_ids=["signal-1", "signal-2"],
            frequency=2,
            average_score=8.4,
            top_examples=["Reporting setup takes too long."],
        )
        return cluster, signals

    @staticmethod
    def _signal(
        signal_id: str,
        *,
        company: str,
        url: str,
        pain: str = "Calendar sync fails.",
        category: str = "Calendar reliability",
        confidence: float = 0.9,
        urgency: str = "medium",
        severity: str = "medium",
    ) -> Signal:
        return Signal.create(
            id=signal_id,
            post_id=signal_id,
            pain=pain,
            user_type="operations teams",
            category=category,
            urgency=urgency,
            severity=severity,
            confidence=confidence,
            niche_company_id=company,
            evidence_url=url,
        )


if __name__ == "__main__":
    unittest.main()

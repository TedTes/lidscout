import unittest

from domain.opportunity import Opportunity


class OpportunityModelTests(unittest.TestCase):
    def test_creates_valid_opportunity(self):
        opportunity = Opportunity.create(
            id=" opportunity-1 ",
            cluster_id=" cluster-1 ",
            title=" Reliable Notion calendar fallback ",
            target_user=" Notion-heavy operations teams ",
            pain_summary=" Users cannot reliably open Notion Calendar. ",
            why_it_matters=" Calendar access blocks daily planning workflows. ",
            suggested_wedge=" Build a lightweight backup calendar view. ",
            evidence_count=3,
            confidence=0.876,
            evidence_signal_ids=[" signal-1 ", "signal-2"],
        )

        self.assertEqual(opportunity.id, "opportunity-1")
        self.assertEqual(opportunity.cluster_id, "cluster-1")
        self.assertEqual(opportunity.title, "Reliable Notion calendar fallback")
        self.assertEqual(opportunity.target_user, "Notion-heavy operations teams")
        self.assertEqual(
            opportunity.pain_summary,
            "Users cannot reliably open Notion Calendar.",
        )
        self.assertEqual(
            opportunity.why_it_matters,
            "Calendar access blocks daily planning workflows.",
        )
        self.assertEqual(
            opportunity.suggested_wedge,
            "Build a lightweight backup calendar view.",
        )
        self.assertEqual(opportunity.evidence_count, 3)
        self.assertEqual(opportunity.confidence, 0.88)
        self.assertEqual(opportunity.evidence_signal_ids, ["signal-1", "signal-2"])

    def test_creates_theme_backed_opportunity_without_cluster(self):
        opportunity = Opportunity.create(
            id="opportunity-1",
            cluster_id=None,
            source_theme_id="theme-1",
            title="Reliable calendar fallback",
            target_user="Notion users",
            pain_summary="Calendar access breaks.",
            why_it_matters="Planning workflows stop.",
            suggested_wedge="Build a backup view.",
            evidence_count=2,
            confidence=0.8,
            evidence_signal_ids=["finding-1", "finding-2"],
        )

        self.assertIsNone(opportunity.cluster_id)
        self.assertEqual(opportunity.source_theme_id, "theme-1")

    def test_rejects_missing_cluster_and_theme(self):
        with self.assertRaises(ValueError):
            Opportunity.create(
                id="opportunity-1",
                cluster_id=None,
                title="Reliable calendar fallback",
                target_user="Notion users",
                pain_summary="Calendar access breaks.",
                why_it_matters="Planning workflows stop.",
                suggested_wedge="Build a backup view.",
                evidence_count=2,
                confidence=0.8,
                evidence_signal_ids=["finding-1", "finding-2"],
            )

    def test_rejects_missing_title(self):
        with self.assertRaises(ValueError):
            Opportunity.create(
                id="opportunity-1",
                cluster_id="cluster-1",
                title=" ",
                target_user="Notion users",
                pain_summary="Calendar access breaks.",
                why_it_matters="Planning workflows stop.",
                suggested_wedge="Build a backup view.",
                evidence_count=1,
                confidence=0.8,
                evidence_signal_ids=["signal-1"],
            )

    def test_rejects_missing_suggested_wedge(self):
        with self.assertRaises(ValueError):
            Opportunity.create(
                id="opportunity-1",
                cluster_id="cluster-1",
                title="Reliable calendar fallback",
                target_user="Notion users",
                pain_summary="Calendar access breaks.",
                why_it_matters="Planning workflows stop.",
                suggested_wedge=" ",
                evidence_count=1,
                confidence=0.8,
                evidence_signal_ids=["signal-1"],
            )

    def test_rejects_empty_evidence(self):
        with self.assertRaises(ValueError):
            Opportunity.create(
                id="opportunity-1",
                cluster_id="cluster-1",
                title="Reliable calendar fallback",
                target_user="Notion users",
                pain_summary="Calendar access breaks.",
                why_it_matters="Planning workflows stop.",
                suggested_wedge="Build a backup view.",
                evidence_count=0,
                confidence=0.8,
                evidence_signal_ids=[],
            )

    def test_rejects_invalid_confidence(self):
        with self.assertRaises(ValueError):
            Opportunity.create(
                id="opportunity-1",
                cluster_id="cluster-1",
                title="Reliable calendar fallback",
                target_user="Notion users",
                pain_summary="Calendar access breaks.",
                why_it_matters="Planning workflows stop.",
                suggested_wedge="Build a backup view.",
                evidence_count=1,
                confidence=1.1,
                evidence_signal_ids=["signal-1"],
            )


if __name__ == "__main__":
    unittest.main()

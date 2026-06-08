from datetime import UTC, datetime

import pytest

from domain.finding import Finding
from domain.signal import Signal
from domain.theme import Theme, ThemeFinding


def test_finding_from_signal_builds_embedding_text():
    signal = Signal.create(
        id="signal:post-1",
        post_id="post-1",
        pain="Exports break on schema changes",
        user_type="analytics engineers",
        job_to_be_done="keep warehouse transforms reliable",
        current_workaround="manual reruns",
        urgency="high",
        severity="medium",
        willingness_to_pay=True,
        category="data reliability",
        confidence=0.81,
        niche_company_id="company-1",
        niche_id="niche-1",
        evidence_url="https://example.com/post-1",
        evidence_text="dbt incremental models break when columns change",
        detected_at=datetime(2026, 6, 8, tzinfo=UTC),
    )

    finding = Finding.from_signal(
        user_niche_id="user-niche-1",
        signal=signal,
        source_id="source-1",
        post_title="Schema change issue",
        embedding=[0.1, 0.2],
    )

    assert finding.user_niche_id == "user-niche-1"
    assert finding.source_id == "source-1"
    assert finding.company_id == "company-1"
    assert finding.affected_user == "analytics engineers"
    assert "Exports break" in finding.structured_embedding_text
    assert finding.embedding == [0.1, 0.2]


def test_finding_requires_embedding_text():
    with pytest.raises(ValueError, match="structured_embedding_text"):
        Finding.create(
            user_niche_id="user-niche-1",
            post_id="post-1",
            pain="Missing alert routing",
            evidence_text="Alert routing is missing",
            structured_embedding_text=" ",
            urgency="medium",
            severity="medium",
            confidence=0.7,
        )


def test_theme_validates_counts_and_status():
    theme = Theme.create(
        user_niche_id="user-niche-1",
        title="Schema change reliability",
        summary="Users struggle with fragile schema changes.",
        finding_count=2,
        source_count=2,
        company_count=1,
        average_confidence=0.75,
        centroid_embedding=[0.2, 0.3],
    )

    assert theme.status == "emerging"
    assert theme.finding_count == 2
    assert theme.centroid_embedding == [0.2, 0.3]


def test_theme_finding_validates_assignment_method():
    assignment = ThemeFinding.create(
        theme_id="theme-1",
        finding_id="finding-1",
        assignment_method="auto_borderline_llm",
        similarity_score=0.76,
        llm_decision={"same_unmet_need": True},
    )

    assert assignment.assignment_method == "auto_borderline_llm"
    assert assignment.llm_decision == {"same_unmet_need": True}

    with pytest.raises(ValueError, match="unsupported assignment_method"):
        ThemeFinding.create(
            theme_id="theme-1",
            finding_id="finding-2",
            assignment_method="topic_match",  # type: ignore[arg-type]
        )

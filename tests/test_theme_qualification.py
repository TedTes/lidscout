from application.opportunity import OpportunitySynthesisContext
from application.theme_memory import qualify_theme_for_opportunity
from domain.finding import Finding
from domain.theme import Theme


def _theme() -> Theme:
    return Theme.create(
        id="c9158d97-9449-4bf2-9ef5-17bb825d522f",
        user_niche_id="8de09fb9-75d0-40d5-b3ea-703ffea6a853",
        title="Schema change reliability",
        summary="Analytics engineers need safer schema changes.",
    )


def _finding(
    post_id: str,
    *,
    source_id: str = "source-1",
    company_id: str | None = "company-1",
    pain: str = "Incremental models break on schema changes",
    affected_user: str | None = "analytics engineers",
    job_to_be_done: str | None = "keep warehouse transforms reliable",
    category: str | None = "data reliability",
    urgency: str = "high",
    severity: str = "medium",
    confidence: float = 0.8,
    metadata: dict | None = None,
) -> Finding:
    return Finding.create(
        user_niche_id="8de09fb9-75d0-40d5-b3ea-703ffea6a853",
        post_id=post_id,
        pain=pain,
        evidence_text=pain,
        structured_embedding_text=pain,
        urgency=urgency,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        confidence=confidence,
        source_id=source_id,
        company_id=company_id,
        affected_user=affected_user,
        job_to_be_done=job_to_be_done,
        category=category,
        metadata=metadata,
    )


def test_qualifies_theme_with_repeated_source_diverse_buyer_pain():
    qualification = qualify_theme_for_opportunity(
        _theme(),
        [_finding("post-1", source_id="source-1"), _finding("post-2", source_id="source-2")],
    )

    assert qualification.qualified is True
    assert qualification.reason is None
    assert qualification.finding_count == 2
    assert qualification.source_count == 2


def test_rejects_thin_theme_with_one_finding():
    qualification = qualify_theme_for_opportunity(_theme(), [_finding("post-1")])

    assert qualification.qualified is False
    assert qualification.reason == "insufficient_evidence"


def test_requires_source_diversity_unless_high_signal_exception():
    weak = qualify_theme_for_opportunity(
        _theme(),
        [_finding("post-1"), _finding("post-2")],
    )
    strong = qualify_theme_for_opportunity(
        _theme(),
        [
            _finding("post-1", metadata={"source_quality_score": "0.9"}),
            _finding("post-2", metadata={"source_quality_score": "0.9"}),
            _finding("post-3", metadata={"source_quality_score": "0.9"}),
        ],
    )

    assert weak.qualified is False
    assert weak.reason == "insufficient_source_diversity"
    assert strong.qualified is True
    assert strong.reason == "qualified_high_signal_exception"


def test_rejects_off_niche_theme():
    qualification = qualify_theme_for_opportunity(
        _theme(),
        [
            _finding("post-1", source_id="source-1"),
            _finding("post-2", source_id="source-2"),
        ],
        OpportunitySynthesisContext(
            niche_name="bookkeeping",
            target_user="small business owners",
            objective="Find accounting workflow gaps",
        ),
    )

    assert qualification.qualified is False
    assert qualification.reason == "off_niche"

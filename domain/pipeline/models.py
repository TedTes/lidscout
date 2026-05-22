"""Pipeline run diagnostic entities."""
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True)
class PipelineRunMetrics:
    """Persisted funnel metrics for one pipeline run."""

    id: str
    ran_at: datetime
    fetched_count: int
    fetch_failed_count: int
    rule_filtered_count: int
    llm_filtered_count: int
    relevance_failed_count: int
    extraction_attempted_count: int
    extracted_count: int
    no_signal_count: int
    extraction_failed_count: int
    signal_inserted_count: int
    scored_count: int
    scoring_failed_count: int
    average_score: float
    embedding_failed_count: int
    clustered_count: int
    cluster_inserted_count: int
    opportunity_synthesized_count: int
    opportunity_inserted_count: int
    opportunity_failed_count: int
    email_sent: bool
    email_error: str | None = None

    @classmethod
    def create(
        cls,
        *,
        fetched_count: int,
        fetch_failed_count: int,
        rule_filtered_count: int,
        llm_filtered_count: int,
        relevance_failed_count: int,
        extraction_attempted_count: int,
        extracted_count: int,
        no_signal_count: int,
        extraction_failed_count: int,
        signal_inserted_count: int,
        scored_count: int,
        scoring_failed_count: int,
        average_score: float,
        embedding_failed_count: int,
        clustered_count: int,
        cluster_inserted_count: int,
        opportunity_synthesized_count: int,
        opportunity_inserted_count: int,
        opportunity_failed_count: int,
        email_sent: bool,
        email_error: str | None = None,
        id: str | None = None,
        ran_at: datetime | None = None,
    ) -> "PipelineRunMetrics":
        """Build validated pipeline run metrics."""
        return cls(
            id=(id or f"pipeline-run-{uuid4().hex}").strip(),
            ran_at=ran_at or datetime.now(tz=UTC),
            fetched_count=_non_negative(fetched_count, "fetched_count"),
            fetch_failed_count=_non_negative(
                fetch_failed_count,
                "fetch_failed_count",
            ),
            rule_filtered_count=_non_negative(
                rule_filtered_count,
                "rule_filtered_count",
            ),
            llm_filtered_count=_non_negative(
                llm_filtered_count,
                "llm_filtered_count",
            ),
            relevance_failed_count=_non_negative(
                relevance_failed_count,
                "relevance_failed_count",
            ),
            extraction_attempted_count=_non_negative(
                extraction_attempted_count,
                "extraction_attempted_count",
            ),
            extracted_count=_non_negative(extracted_count, "extracted_count"),
            no_signal_count=_non_negative(no_signal_count, "no_signal_count"),
            extraction_failed_count=_non_negative(
                extraction_failed_count,
                "extraction_failed_count",
            ),
            signal_inserted_count=_non_negative(
                signal_inserted_count,
                "signal_inserted_count",
            ),
            scored_count=_non_negative(scored_count, "scored_count"),
            scoring_failed_count=_non_negative(
                scoring_failed_count,
                "scoring_failed_count",
            ),
            average_score=float(average_score),
            embedding_failed_count=_non_negative(
                embedding_failed_count,
                "embedding_failed_count",
            ),
            clustered_count=_non_negative(clustered_count, "clustered_count"),
            cluster_inserted_count=_non_negative(
                cluster_inserted_count,
                "cluster_inserted_count",
            ),
            opportunity_synthesized_count=_non_negative(
                opportunity_synthesized_count,
                "opportunity_synthesized_count",
            ),
            opportunity_inserted_count=_non_negative(
                opportunity_inserted_count,
                "opportunity_inserted_count",
            ),
            opportunity_failed_count=_non_negative(
                opportunity_failed_count,
                "opportunity_failed_count",
            ),
            email_sent=email_sent,
            email_error=email_error.strip() if email_error else None,
        )


def _non_negative(value: int, field_name: str) -> int:
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value

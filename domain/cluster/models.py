"""Domain models for clustered signals."""
from dataclasses import dataclass

from domain.score.severity import Severity, severity_for_frequency


@dataclass(frozen=True)
class SignalCluster:
    """Grouped market signals around a recurring theme."""

    id: str
    theme: str
    summary: str
    signal_ids: list[str]
    frequency: int
    average_score: float
    top_examples: list[str]

    @classmethod
    def create(
        cls,
        *,
        id: str,
        theme: str,
        summary: str,
        signal_ids: list[str],
        frequency: int,
        average_score: float,
        top_examples: list[str] | None = None,
    ) -> "SignalCluster":
        """Create a validated signal cluster entity."""
        cluster_id = id.strip()
        normalized_theme = theme.strip()
        normalized_summary = summary.strip()
        normalized_signal_ids = [
            str(signal_id).strip()
            for signal_id in signal_ids
            if str(signal_id).strip()
        ]
        normalized_examples = [
            example.strip()
            for example in top_examples or []
            if example.strip()
        ]

        if not cluster_id:
            raise ValueError("id is required")
        if not normalized_theme:
            raise ValueError("theme is required")
        if not normalized_summary:
            raise ValueError("summary is required")
        if not normalized_signal_ids:
            raise ValueError("signal_ids is required")
        if frequency < 0:
            raise ValueError("frequency must be non-negative")
        if not 0.0 <= average_score <= 10.0:
            raise ValueError("average_score must be between 0.0 and 10.0")

        return cls(
            id=cluster_id,
            theme=normalized_theme,
            summary=normalized_summary,
            signal_ids=normalized_signal_ids,
            frequency=frequency,
            average_score=round(average_score, 2),
            top_examples=normalized_examples,
        )

    @property
    def severity(self) -> Severity:
        """Compatibility severity derived from cluster frequency."""
        return severity_for_frequency(self.frequency)

    @property
    def interaction_ids(self) -> list[str]:
        """Compatibility alias for older interaction-based extraction."""
        return self.signal_ids

    @property
    def excerpts(self) -> list[str]:
        """Compatibility alias for older interaction-based extraction."""
        return self.top_examples

"""Source input model."""
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
from typing import Any
from typing import Literal
from urllib.parse import urlparse

ValidationStatus = Literal["unknown", "valid", "invalid"]


@dataclass(frozen=True)
class SourceInput:
    """A source locator submitted to the signal pipeline."""

    locator: str
    limit: int | None = None
    options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        locator: str,
        limit: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> "SourceInput":
        """Build a normalized source input."""
        normalized_locator = locator.strip()
        if not normalized_locator:
            raise ValueError("locator is required")

        if limit is not None and limit < 1:
            raise ValueError("limit must be at least 1")

        return cls(
            locator=normalized_locator,
            limit=limit,
            options=options or {},
        )


@dataclass(frozen=True)
class SourceLocator:
    """A whitelisted locator that the pipeline can scan automatically."""

    id: str
    locator: str
    enabled: bool = True
    limit: int | None = None
    options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        locator: str,
        id: str | None = None,
        enabled: bool = True,
        limit: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> "SourceLocator":
        """Build a normalized source locator."""
        source_input = SourceInput.create(
            locator=locator,
            limit=limit,
            options=options,
        )
        locator_id = (id or _source_locator_id(source_input.locator)).strip()
        if not locator_id:
            raise ValueError("id is required")

        return cls(
            id=locator_id,
            locator=source_input.locator,
            enabled=enabled,
            limit=source_input.limit,
            options=source_input.options,
        )

    def to_source_input(self) -> SourceInput:
        """Convert a configured locator into a pipeline source input."""
        return SourceInput.create(
            locator=self.locator,
            limit=self.limit,
            options=self.options,
        )


def _source_locator_id(locator: str) -> str:
    digest = hashlib.sha256(locator.encode("utf-8")).hexdigest()[:16]
    return f"source-locator-{digest}"


@dataclass(frozen=True)
class MonitoredSource:
    """A market or competitor-linked source scanned by the background pipeline."""

    id: str
    locator: str
    source_type: str
    competitor_id: str | None = None
    market_id: str | None = None
    enabled: bool = True
    limit: int | None = None
    scan_frequency: str | None = None
    last_scanned_at: datetime | None = None
    last_error: str | None = None
    options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        locator: str,
        competitor_id: str | None = None,
        market_id: str | None = None,
        id: str | None = None,
        source_type: str = "web",
        enabled: bool = True,
        limit: int | None = None,
        scan_frequency: str | None = None,
        last_scanned_at: datetime | None = None,
        last_error: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> "MonitoredSource":
        """Build a validated monitored source."""
        normalized_competitor_id = _clean_optional(competitor_id)
        normalized_market_id = _clean_optional(market_id)
        if normalized_competitor_id is None and normalized_market_id is None:
            raise ValueError("competitor_id or market_id is required")

        source_input = SourceInput.create(
            locator=locator,
            limit=limit,
            options=options,
        )
        _validate_supported_locator(source_input.locator)

        source_scope = normalized_competitor_id or normalized_market_id
        source_id = (
            id or _monitored_source_id(source_scope or "", source_input.locator)
        ).strip()
        normalized_source_type = source_type.strip().lower()
        if not source_id:
            raise ValueError("id is required")
        if not normalized_source_type:
            raise ValueError("source_type is required")

        return cls(
            id=source_id,
            locator=source_input.locator,
            source_type=normalized_source_type,
            competitor_id=normalized_competitor_id,
            market_id=normalized_market_id,
            enabled=enabled,
            limit=source_input.limit,
            scan_frequency=_clean_optional(scan_frequency),
            last_scanned_at=last_scanned_at,
            last_error=_clean_optional(last_error),
            options=source_input.options,
        )

    def to_source_input(self) -> SourceInput:
        """Convert a monitored source into a pipeline source input with context."""
        options = {
            **self.options,
            "monitored_source_id": self.id,
            "source_type": self.source_type,
        }
        if self.competitor_id:
            options["competitor_id"] = self.competitor_id
        if self.market_id:
            options["market_id"] = self.market_id
        return SourceInput.create(
            locator=self.locator,
            limit=self.limit,
            options=options,
        )


@dataclass(frozen=True)
class SourceTemplate:
    """Reusable rule for rendering source candidates from market/company context."""

    id: str
    label: str
    source_type: str
    url_template: str
    source_family: str
    default_limit: int | None = None
    applicable_categories: list[str] = field(default_factory=list)
    enabled: bool = True
    rank_score: float = 0.0
    options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        id: str,
        label: str,
        source_type: str,
        url_template: str,
        source_family: str,
        default_limit: int | None = None,
        applicable_categories: list[str] | None = None,
        enabled: bool = True,
        rank_score: float = 0.0,
        options: dict[str, Any] | None = None,
    ) -> "SourceTemplate":
        """Build a validated source template."""
        template_id = id.strip()
        normalized_label = label.strip()
        normalized_source_type = source_type.strip().lower()
        normalized_url_template = url_template.strip()
        normalized_source_family = source_family.strip().lower()
        normalized_categories = _clean_list(applicable_categories or [])

        if not template_id:
            raise ValueError("id is required")
        if not normalized_label:
            raise ValueError("label is required")
        if not normalized_source_type:
            raise ValueError("source_type is required")
        if not normalized_url_template:
            raise ValueError("url_template is required")
        if not normalized_source_family:
            raise ValueError("source_family is required")
        if default_limit is not None and default_limit < 1:
            raise ValueError("default_limit must be at least 1")
        if rank_score < 0.0:
            raise ValueError("rank_score must be non-negative")

        return cls(
            id=template_id,
            label=normalized_label,
            source_type=normalized_source_type,
            url_template=normalized_url_template,
            source_family=normalized_source_family,
            default_limit=default_limit,
            applicable_categories=normalized_categories,
            enabled=enabled,
            rank_score=rank_score,
            options=options or {},
        )

    def applies_to_any_category(self, categories: list[str]) -> bool:
        """Return whether this template applies to at least one supplied category."""
        if not self.applicable_categories:
            return True
        normalized_categories = set(_clean_list(categories))
        return bool(normalized_categories.intersection(self.applicable_categories))


@dataclass(frozen=True)
class SourceCandidate:
    """Rendered source candidate shown to an admin before monitoring is enabled."""

    locator: str
    source_type: str
    label: str
    rationale: str
    source_family: str
    limit: int | None = None
    options: dict[str, Any] = field(default_factory=dict)
    template_id: str | None = None
    already_monitored: bool = False
    rank_score: float = 0.0
    validation_status: ValidationStatus = "unknown"
    validation_error: str | None = None

    @classmethod
    def create(
        cls,
        *,
        locator: str,
        source_type: str,
        label: str,
        rationale: str,
        source_family: str,
        limit: int | None = None,
        options: dict[str, Any] | None = None,
        template_id: str | None = None,
        already_monitored: bool = False,
        rank_score: float = 0.0,
        validation_status: ValidationStatus = "unknown",
        validation_error: str | None = None,
    ) -> "SourceCandidate":
        """Build a validated rendered source candidate."""
        source_input = SourceInput.create(
            locator=locator,
            limit=limit,
            options=options,
        )
        normalized_source_type = source_type.strip().lower()
        normalized_label = label.strip()
        normalized_rationale = rationale.strip()
        normalized_source_family = source_family.strip().lower()

        if not normalized_source_type:
            raise ValueError("source_type is required")
        if not normalized_label:
            raise ValueError("label is required")
        if not normalized_rationale:
            raise ValueError("rationale is required")
        if not normalized_source_family:
            raise ValueError("source_family is required")
        if rank_score < 0.0:
            raise ValueError("rank_score must be non-negative")
        if validation_status not in {"unknown", "valid", "invalid"}:
            raise ValueError("validation_status must be unknown, valid, or invalid")

        return cls(
            locator=source_input.locator,
            source_type=normalized_source_type,
            label=normalized_label,
            rationale=normalized_rationale,
            source_family=normalized_source_family,
            limit=source_input.limit,
            options=source_input.options,
            template_id=_clean_optional(template_id),
            already_monitored=already_monitored,
            rank_score=rank_score,
            validation_status=validation_status,
            validation_error=_clean_optional(validation_error),
        )


def _monitored_source_id(competitor_id: str, locator: str) -> str:
    digest = hashlib.sha256(f"{competitor_id}:{locator}".encode("utf-8")).hexdigest()[
        :16
    ]
    return f"monitored-source-{digest}"


def _validate_supported_locator(locator: str) -> None:
    parsed = urlparse(locator)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("locator must be an http or https URL")


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_list(values: list[str]) -> list[str]:
    cleaned_values = []
    seen = set()
    for value in values:
        cleaned = value.strip().lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        cleaned_values.append(cleaned)
    return cleaned_values

"""Source input model."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
from typing import Any
from typing import Literal
import uuid
from urllib.parse import urlparse

ValidationStatus = Literal["unknown", "valid", "invalid"]
TemplateScope = Literal["company", "market"]
SourceHealthStatus = Literal["unknown", "healthy", "failing"]
SourceAccessMode = Literal[
    "unknown",
    "api",
    "api_auth",
    "json",
    "rss",
    "html",
    "proxy_required",
    "manual",
]
SourceReplacementTrigger = Literal[
    "blocked_source",
    "low_yield",
    "stale_source",
    "missing_family",
]


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


@dataclass(frozen=True)
class Source:
    """Canonical source identity shared across template and user scopes."""

    id: str
    locator: str
    source_type: str
    source_family: str
    is_gate_free: bool = False
    access_mode: SourceAccessMode = "unknown"
    requires_proxy: bool = False
    requires_auth: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        locator: str,
        source_type: str,
        source_family: str,
        id: str | None = None,
        is_gate_free: bool = False,
        access_mode: str = "unknown",
        requires_proxy: bool = False,
        requires_auth: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "Source":
        """Build a normalized canonical source."""
        source_id = (id or str(uuid.uuid4())).strip()
        normalized_locator = locator.strip()
        normalized_source_type = source_type.strip().lower()
        normalized_source_family = source_family.strip().lower()
        normalized_access_mode = access_mode.strip().lower()
        if not source_id:
            raise ValueError("id is required")
        if not normalized_locator:
            raise ValueError("locator is required")
        if not normalized_source_type:
            raise ValueError("source_type is required")
        if not normalized_source_family:
            raise ValueError("source_family is required")
        if normalized_access_mode not in {
            "unknown",
            "api",
            "api_auth",
            "json",
            "rss",
            "html",
            "proxy_required",
            "manual",
        }:
            raise ValueError("unsupported access_mode")
        now = datetime.now(tz=UTC)
        return cls(
            id=source_id,
            locator=normalized_locator,
            source_type=normalized_source_type,
            source_family=normalized_source_family,
            is_gate_free=is_gate_free,
            access_mode=normalized_access_mode,  # type: ignore[arg-type]
            requires_proxy=requires_proxy,
            requires_auth=requires_auth,
            created_at=created_at or now,
            updated_at=updated_at or now,
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
class SourceHealth:
    """Cumulative health and yield memory for one monitored source."""

    monitored_source_id: str
    total_runs: int = 0
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    posts_fetched_count: int = 0
    relevant_posts_count: int = 0
    extracted_signals_count: int = 0
    opportunity_count: int = 0
    last_status: SourceHealthStatus = "unknown"
    last_error: str | None = None
    last_fetched_count: int = 0
    last_relevant_count: int = 0
    last_extracted_count: int = 0
    last_opportunity_count: int = 0
    last_scanned_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        monitored_source_id: str,
        total_runs: int = 0,
        success_count: int = 0,
        failure_count: int = 0,
        consecutive_failures: int = 0,
        posts_fetched_count: int = 0,
        relevant_posts_count: int = 0,
        extracted_signals_count: int = 0,
        opportunity_count: int = 0,
        last_status: SourceHealthStatus = "unknown",
        last_error: str | None = None,
        last_fetched_count: int = 0,
        last_relevant_count: int = 0,
        last_extracted_count: int = 0,
        last_opportunity_count: int = 0,
        last_scanned_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "SourceHealth":
        """Build a validated source health snapshot."""
        source_id = monitored_source_id.strip()
        if not source_id:
            raise ValueError("monitored_source_id is required")
        if last_status not in {"unknown", "healthy", "failing"}:
            raise ValueError("last_status must be unknown, healthy, or failing")

        counts = {
            "total_runs": total_runs,
            "success_count": success_count,
            "failure_count": failure_count,
            "consecutive_failures": consecutive_failures,
            "posts_fetched_count": posts_fetched_count,
            "relevant_posts_count": relevant_posts_count,
            "extracted_signals_count": extracted_signals_count,
            "opportunity_count": opportunity_count,
            "last_fetched_count": last_fetched_count,
            "last_relevant_count": last_relevant_count,
            "last_extracted_count": last_extracted_count,
            "last_opportunity_count": last_opportunity_count,
        }
        for name, value in counts.items():
            if value < 0:
                raise ValueError(f"{name} must be non-negative")

        return cls(
            monitored_source_id=source_id,
            total_runs=total_runs,
            success_count=success_count,
            failure_count=failure_count,
            consecutive_failures=consecutive_failures,
            posts_fetched_count=posts_fetched_count,
            relevant_posts_count=relevant_posts_count,
            extracted_signals_count=extracted_signals_count,
            opportunity_count=opportunity_count,
            last_status=last_status,
            last_error=_clean_optional(last_error),
            last_fetched_count=last_fetched_count,
            last_relevant_count=last_relevant_count,
            last_extracted_count=last_extracted_count,
            last_opportunity_count=last_opportunity_count,
            last_scanned_at=last_scanned_at,
            updated_at=updated_at,
        )

    def record_run(
        self,
        *,
        fetched_count: int,
        relevant_count: int,
        extracted_count: int,
        opportunity_count: int,
        error: str | None,
        scanned_at: datetime,
    ) -> "SourceHealth":
        """Return a new snapshot with one source run folded in."""
        failed = error is not None
        return SourceHealth.create(
            monitored_source_id=self.monitored_source_id,
            total_runs=self.total_runs + 1,
            success_count=self.success_count + (0 if failed else 1),
            failure_count=self.failure_count + (1 if failed else 0),
            consecutive_failures=(
                self.consecutive_failures + 1 if failed else 0
            ),
            posts_fetched_count=self.posts_fetched_count + fetched_count,
            relevant_posts_count=self.relevant_posts_count + relevant_count,
            extracted_signals_count=(
                self.extracted_signals_count + extracted_count
            ),
            opportunity_count=self.opportunity_count + opportunity_count,
            last_status="failing" if failed else "healthy",
            last_error=error,
            last_fetched_count=fetched_count,
            last_relevant_count=relevant_count,
            last_extracted_count=extracted_count,
            last_opportunity_count=opportunity_count,
            last_scanned_at=scanned_at,
            updated_at=scanned_at,
        )

    @property
    def fetch_success_rate(self) -> float:
        """Return cumulative fetch success rate."""
        return round(self.success_count / self.total_runs, 4) if self.total_runs else 0.0

    @property
    def relevance_yield_rate(self) -> float:
        """Return cumulative relevant-post yield over fetched posts."""
        return (
            round(self.relevant_posts_count / self.posts_fetched_count, 4)
            if self.posts_fetched_count
            else 0.0
        )

    @property
    def signal_yield_rate(self) -> float:
        """Return cumulative extracted-signal yield over fetched posts."""
        return (
            round(self.extracted_signals_count / self.posts_fetched_count, 4)
            if self.posts_fetched_count
            else 0.0
        )


@dataclass(frozen=True)
class SourceTemplate:
    """Reusable rule for rendering source candidates from market/company context."""

    id: str
    label: str
    source_type: str
    url_template: str
    source_family: str
    rationale: str
    scope: TemplateScope = "company"
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
        rationale: str,
        scope: TemplateScope = "company",
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
        normalized_rationale = rationale.strip()
        normalized_scope = scope.strip().lower()
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
        if not normalized_rationale:
            raise ValueError("rationale is required")
        if normalized_scope not in {"company", "market"}:
            raise ValueError("scope must be company or market")
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
            rationale=normalized_rationale,
            scope=normalized_scope,  # type: ignore[arg-type]
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
    competitor_id: str | None = None
    competitor_name: str | None = None
    market_id: str | None = None
    market_name: str | None = None
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
        competitor_id: str | None = None,
        competitor_name: str | None = None,
        market_id: str | None = None,
        market_name: str | None = None,
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
            competitor_id=_clean_optional(competitor_id),
            competitor_name=_clean_optional(competitor_name),
            market_id=_clean_optional(market_id),
            market_name=_clean_optional(market_name),
            limit=source_input.limit,
            options=source_input.options,
            template_id=_clean_optional(template_id),
            already_monitored=already_monitored,
            rank_score=rank_score,
            validation_status=validation_status,
            validation_error=_clean_optional(validation_error),
        )


@dataclass(frozen=True)
class SourceReplacementSuggestion:
    """A candidate source proposed to fix or improve current coverage."""

    candidate: SourceCandidate
    trigger: SourceReplacementTrigger
    reason: str
    replaces_source_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        candidate: SourceCandidate,
        trigger: str,
        reason: str,
        replaces_source_id: str | None = None,
    ) -> "SourceReplacementSuggestion":
        normalized_trigger = trigger.strip().lower()
        normalized_reason = reason.strip()
        if normalized_trigger not in {
            "blocked_source",
            "low_yield",
            "stale_source",
            "missing_family",
        }:
            raise ValueError("unsupported replacement trigger")
        if not normalized_reason:
            raise ValueError("reason is required")
        return cls(
            candidate=candidate,
            trigger=normalized_trigger,  # type: ignore[arg-type]
            reason=normalized_reason,
            replaces_source_id=_clean_optional(replaces_source_id),
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

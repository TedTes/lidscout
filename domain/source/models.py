"""Source input model."""
from dataclasses import dataclass, field
import hashlib
from typing import Any


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

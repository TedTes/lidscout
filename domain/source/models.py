"""Source input model."""
from dataclasses import dataclass, field
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

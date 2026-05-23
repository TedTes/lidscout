"""Competitor domain entities."""
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class Competitor:
    """A competitor monitored for customer complaints and market gaps."""

    id: str
    name: str
    website: str | None = None
    category: str | None = None
    description: str | None = None
    market_id: str | None = None
    created_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        id: str,
        name: str,
        website: str | None = None,
        category: str | None = None,
        description: str | None = None,
        market_id: str | None = None,
        created_at: datetime | None = None,
    ) -> "Competitor":
        """Create a validated competitor entity."""
        competitor_id = id.strip()
        normalized_name = name.strip()
        if not competitor_id:
            raise ValueError("id is required")
        if not normalized_name:
            raise ValueError("name is required")

        return cls(
            id=competitor_id,
            name=normalized_name,
            website=cls._clean_optional(website),
            category=cls._clean_optional(category),
            description=cls._clean_optional(description),
            market_id=cls._clean_optional(market_id),
            created_at=created_at or datetime.now(tz=UTC),
        )

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

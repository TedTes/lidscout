"""Market domain entities."""
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class Market:
    """A niche or category watched for cross-company pain patterns."""

    id: str
    name: str
    description: str | None = None
    target_user: str | None = None
    idea_prompt: str | None = None
    user_id: str | None = None
    # Which template this niche was seeded from. Preserved for future
    # "reset to defaults" / template-diff features. Never mutated after creation.
    template_id: str | None = None
    created_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        id: str,
        name: str,
        description: str | None = None,
        target_user: str | None = None,
        idea_prompt: str | None = None,
        user_id: str | None = None,
        template_id: str | None = None,
        created_at: datetime | None = None,
    ) -> "Market":
        """Create a validated market entity."""
        market_id = id.strip()
        normalized_name = name.strip()
        if not market_id:
            raise ValueError("id is required")
        if not normalized_name:
            raise ValueError("name is required")

        return cls(
            id=market_id,
            name=normalized_name,
            description=cls._clean_optional(description),
            target_user=cls._clean_optional(target_user),
            idea_prompt=cls._clean_optional(idea_prompt),
            user_id=user_id,
            template_id=template_id,
            created_at=created_at or datetime.now(tz=UTC),
        )

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

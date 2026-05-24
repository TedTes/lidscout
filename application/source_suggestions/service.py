"""Source suggestion service for competitor monitoring."""
import re

from application.source_suggestions.default_templates import get_default_source_templates
from application.source_suggestions.template_renderer import render_source_candidates
from application.source_suggestions.validation import validate_source_candidates
from domain.competitor import Competitor
from domain.market import Market
from domain.source import MonitoredSource, SourceCandidate, SourceTemplate

SourceSuggestion = SourceCandidate


class SourceSuggestionService:
    """Build source candidates from reusable templates."""

    def __init__(self, templates: list[SourceTemplate] | None = None) -> None:
        self.templates = templates or get_default_source_templates()

    def suggest(
        self,
        competitor: Competitor,
        existing_sources: list[MonitoredSource] | None = None,
        *,
        market: Market | None = None,
    ) -> list[SourceSuggestion]:
        """Return rendered source suggestions for a competitor and optional market."""
        existing_locators = {
            source.locator
            for source in existing_sources or []
        }
        candidates = render_source_candidates(
            self._applicable_templates(competitor=competitor, market=market),
            competitor=competitor,
            market=market,
            existing_locators=existing_locators,
        )
        return validate_source_candidates(candidates)

    def suggest_for_market(
        self,
        market: Market,
        existing_sources: list[MonitoredSource] | None = None,
    ) -> list[SourceSuggestion]:
        """Return rendered source suggestions for a market-level watchlist."""
        existing_locators = {
            source.locator
            for source in existing_sources or []
        }
        candidates = render_source_candidates(
            self._applicable_templates(competitor=None, market=market),
            market=market,
            existing_locators=existing_locators,
        )
        return validate_source_candidates(candidates)

    def _applicable_templates(
        self,
        *,
        competitor: Competitor | None,
        market: Market | None,
    ) -> list[SourceTemplate]:
        categories = _template_categories(competitor=competitor, market=market)
        if not categories:
            return [template for template in self.templates if template.enabled]
        return [
            template
            for template in self.templates
            if template.enabled and template.applies_to_any_category(categories)
        ]


def _template_categories(
    *,
    competitor: Competitor | None,
    market: Market | None,
) -> list[str]:
    categories = []
    if competitor is not None and competitor.category:
        categories.append(competitor.category)
    if market is not None:
        categories.extend([market.id, market.name])
    return _category_aliases(categories)


def _category_aliases(values: list[str]) -> list[str]:
    aliases: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip().lower()
        if not cleaned:
            continue
        words = [part for part in re.split(r"[^a-z0-9]+", cleaned) if part]
        variants = {
            cleaned,
            "_".join(words),
            "-".join(words),
            *words,
        }
        for variant in variants:
            if variant and variant not in seen:
                aliases.append(variant)
                seen.add(variant)
    return aliases

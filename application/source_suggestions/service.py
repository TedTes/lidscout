"""Source suggestion service for competitor monitoring."""
from dataclasses import dataclass, field
from urllib.parse import quote_plus, urlparse

from domain.competitor import Competitor
from domain.source import MonitoredSource


@dataclass(frozen=True)
class SourceSuggestion:
    """A candidate source an admin can add to a competitor watchlist."""

    locator: str
    source_type: str
    label: str
    rationale: str
    limit: int | None = None
    options: dict[str, str] = field(default_factory=dict)
    already_monitored: bool = False


class SourceSuggestionService:
    """Builds opinionated default source candidates for a competitor."""

    def suggest(
        self,
        competitor: Competitor,
        existing_sources: list[MonitoredSource] | None = None,
    ) -> list[SourceSuggestion]:
        existing_locators = {
            source.locator.rstrip("/")
            for source in existing_sources or []
        }
        suggestions = self._candidate_suggestions(competitor)
        return [
            _mark_existing(suggestion, existing_locators)
            for suggestion in _dedupe_suggestions(suggestions)
        ]

    def _candidate_suggestions(self, competitor: Competitor) -> list[SourceSuggestion]:
        query = quote_plus(competitor.name)
        suggestions = [
            SourceSuggestion(
                locator=f"https://www.reddit.com/search.json?q={query}&sort=new",
                source_type="reddit_search",
                label="Reddit search",
                rationale="Find recent public discussions and complaints mentioning the competitor.",
                limit=25,
                options={"adapter": "json", "source_family": "social"},
            ),
            SourceSuggestion(
                locator=(
                    "https://hn.algolia.com/api/v1/search_by_date"
                    f"?query={query}&tags=story"
                ),
                source_type="hackernews_search",
                label="Hacker News search",
                rationale="Find technical buyer and founder discussions mentioning the competitor.",
                limit=25,
                options={"adapter": "json", "source_family": "technical_forum"},
            ),
            SourceSuggestion(
                locator=f"https://www.g2.com/search?query={query}",
                source_type="review_search",
                label="G2 search",
                rationale="Surface B2B software review pages and competitor comparisons.",
                limit=10,
                options={"adapter": "static", "source_family": "reviews"},
            ),
            SourceSuggestion(
                locator=f"https://www.capterra.com/search/?query={query}",
                source_type="review_search",
                label="Capterra search",
                rationale="Surface review and category pages for recurring customer pain.",
                limit=10,
                options={"adapter": "static", "source_family": "reviews"},
            ),
        ]

        if competitor.website:
            website = competitor.website.rstrip("/")
            domain = _domain_label(website)
            suggestions.extend(
                [
                    SourceSuggestion(
                        locator=website,
                        source_type="website",
                        label=f"{domain} website",
                        rationale="Monitor public product and positioning changes from the competitor.",
                        limit=1,
                        options={"adapter": "static", "source_family": "owned_site"},
                    ),
                    SourceSuggestion(
                        locator=f"{website}/changelog",
                        source_type="changelog",
                        label=f"{domain} changelog",
                        rationale="Track product changes that may respond to customer complaints.",
                        limit=5,
                        options={"adapter": "static", "source_family": "owned_site"},
                    ),
                    SourceSuggestion(
                        locator=f"{website}/blog",
                        source_type="blog",
                        label=f"{domain} blog",
                        rationale="Track product announcements and customer-facing roadmap signals.",
                        limit=10,
                        options={"adapter": "static", "source_family": "owned_site"},
                    ),
                ]
            )

        return suggestions


def _mark_existing(
    suggestion: SourceSuggestion,
    existing_locators: set[str],
) -> SourceSuggestion:
    return SourceSuggestion(
        locator=suggestion.locator,
        source_type=suggestion.source_type,
        label=suggestion.label,
        rationale=suggestion.rationale,
        limit=suggestion.limit,
        options=suggestion.options,
        already_monitored=suggestion.locator.rstrip("/") in existing_locators,
    )


def _dedupe_suggestions(suggestions: list[SourceSuggestion]) -> list[SourceSuggestion]:
    seen = set()
    deduped = []
    for suggestion in suggestions:
        key = suggestion.locator.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(suggestion)
    return deduped


def _domain_label(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc or "competitor"

"""Render source templates into concrete source candidates."""
from __future__ import annotations

import re
from string import Formatter
from typing import Any
from urllib.parse import quote_plus, urlparse

from domain.competitor import Competitor
from domain.market import Market
from domain.source import SourceCandidate, SourceTemplate


def render_source_candidate(
    template: SourceTemplate,
    *,
    competitor: Competitor | None = None,
    market: Market | None = None,
    already_monitored: bool = False,
) -> SourceCandidate | None:
    """Render one enabled template, or return None when context is incomplete."""
    if not template.enabled:
        return None

    variables = _template_variables(competitor=competitor, market=market)
    locator = _render_string(template.url_template, variables)
    label = _render_string(template.label, variables)
    rationale = _render_string(template.rationale, variables)
    if locator is None or label is None or rationale is None:
        return None

    options = _render_options(template.options, variables)
    if options is None:
        return None

    return SourceCandidate.create(
        locator=locator,
        source_type=template.source_type,
        label=label,
        rationale=rationale,
        source_family=template.source_family,
        competitor_id=competitor.id if competitor else None,
        competitor_name=competitor.name if competitor else None,
        market_id=market.id if market else competitor.market_id if competitor else None,
        market_name=market.name if market else None,
        limit=template.default_limit,
        options=options,
        template_id=template.id,
        already_monitored=already_monitored,
        rank_score=template.rank_score,
        validation_status="unknown",
    )


def render_source_candidates(
    templates: list[SourceTemplate],
    *,
    competitor: Competitor | None = None,
    market: Market | None = None,
    existing_locators: set[str] | None = None,
) -> list[SourceCandidate]:
    """Render templates and de-dupe concrete candidates by normalized locator."""
    normalized_existing = {
        _normalize_locator(locator) for locator in existing_locators or set()
    }
    candidates: list[SourceCandidate] = []
    seen: set[str] = set()

    for template in templates:
        candidate = render_source_candidate(
            template,
            competitor=competitor,
            market=market,
            already_monitored=False,
        )
        if candidate is None:
            continue

        locator_key = _normalize_locator(candidate.locator)
        if locator_key in seen:
            continue
        seen.add(locator_key)
        if locator_key in normalized_existing:
            candidate = SourceCandidate.create(
                locator=candidate.locator,
                source_type=candidate.source_type,
                label=candidate.label,
                rationale=candidate.rationale,
                source_family=candidate.source_family,
                competitor_id=candidate.competitor_id,
                competitor_name=candidate.competitor_name,
                market_id=candidate.market_id,
                market_name=candidate.market_name,
                limit=candidate.limit,
                options=candidate.options,
                template_id=candidate.template_id,
                already_monitored=True,
                rank_score=candidate.rank_score,
                validation_status=candidate.validation_status,
                validation_error=candidate.validation_error,
            )
        candidates.append(candidate)

    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.already_monitored,
            -candidate.rank_score,
            candidate.label,
        ),
    )


def _template_variables(
    *,
    competitor: Competitor | None,
    market: Market | None,
) -> dict[str, str]:
    values: dict[str, str] = {}

    if competitor is not None:
        website = _clean_url(competitor.website)
        domain = _domain_from_url(website) if website else None
        values.update(
            _without_empty(
                {
                    "competitor_id": competitor.id,
                    "company_id": competitor.id,
                    "company_name": competitor.name,
                    "company_slug": _slugify(competitor.name),
                    "company_query": quote_plus(competitor.name),
                    "website": website,
                    "domain": domain,
                    "category": competitor.category,
                    "market_category": competitor.category,
                    "market_id": competitor.market_id,
                }
            )
        )

    if market is not None:
        values.update(
            _without_empty(
                {
                    "market_id": market.id,
                    "market_name": market.name,
                    "market_slug": _slugify(market.name),
                    "market_query": quote_plus(market.name),
                    "market_description": market.description,
                    "target_user": market.target_user,
                    "idea_prompt": market.idea_prompt,
                }
            )
        )

    return values


def _render_string(template_value: str, variables: dict[str, str]) -> str | None:
    required_fields = _required_fields(template_value)
    if any(field not in variables for field in required_fields):
        return None
    return template_value.format(**variables).strip()


def _render_options(
    options: dict[str, Any],
    variables: dict[str, str],
) -> dict[str, Any] | None:
    rendered: dict[str, Any] = {}
    for key, value in options.items():
        if isinstance(value, str):
            rendered_value = _render_string(value, variables)
            if rendered_value is None:
                return None
            rendered[key] = rendered_value
        else:
            rendered[key] = value
    return rendered


def _required_fields(template_value: str) -> set[str]:
    fields: set[str] = set()
    for _, field_name, _, _ in Formatter().parse(template_value):
        if field_name:
            fields.add(field_name.split(".", maxsplit=1)[0].split("[", maxsplit=1)[0])
    return fields


def _normalize_locator(locator: str) -> str:
    return locator.strip().rstrip("/")


def _clean_url(url: str | None) -> str | None:
    if url is None:
        return None
    cleaned = url.strip().rstrip("/")
    return cleaned or None


def _domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "source"


def _without_empty(values: dict[str, str | None]) -> dict[str, str]:
    return {
        key: value.strip()
        for key, value in values.items()
        if value is not None and value.strip()
    }

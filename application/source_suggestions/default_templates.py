"""Default source templates for MVP source suggestions."""
from domain.source import SourceTemplate


DEFAULT_SOURCE_TEMPLATES: tuple[SourceTemplate, ...] = (
    SourceTemplate.create(
        id="reddit-company-search",
        label="Reddit mentions",
        source_type="reddit_search",
        url_template="https://www.reddit.com/search.json?q={company_query}&sort=new",
        source_family="social",
        rationale="Find recent public complaints and discussions mentioning {company_name}.",
        default_limit=25,
        rank_score=0.85,
        options={"adapter": "json", "source_family": "social"},
    ),
    SourceTemplate.create(
        id="hackernews-company-search",
        label="Hacker News mentions",
        source_type="hackernews_search",
        url_template=(
            "https://hn.algolia.com/api/v1/search_by_date"
            "?query={company_query}&tags=story"
        ),
        source_family="technical_forum",
        rationale="Find technical buyer and founder discussions mentioning {company_name}.",
        default_limit=25,
        applicable_categories=["ai_tools", "b2b_saas", "devtools", "productivity"],
        rank_score=0.78,
        options={"adapter": "json", "source_family": "technical_forum"},
    ),
    SourceTemplate.create(
        id="g2-company-search",
        label="G2 reviews",
        source_type="review_search",
        url_template="https://www.g2.com/search?query={company_query}",
        source_family="reviews",
        rationale="Surface B2B software reviews and competitor comparisons for {company_name}.",
        default_limit=10,
        applicable_categories=[
            "ai_tools",
            "b2b_saas",
            "devtools",
            "productivity",
            "project_management",
            "vertical_saas",
        ],
        rank_score=0.9,
        options={"adapter": "static", "source_family": "reviews"},
    ),
    SourceTemplate.create(
        id="capterra-company-search",
        label="Capterra reviews",
        source_type="review_search",
        url_template="https://www.capterra.com/search/?query={company_query}",
        source_family="reviews",
        rationale="Surface review and category pages with recurring customer pain for {company_name}.",
        default_limit=10,
        applicable_categories=[
            "b2b_saas",
            "productivity",
            "project_management",
            "vertical_saas",
        ],
        rank_score=0.82,
        options={"adapter": "static", "source_family": "reviews"},
    ),
    SourceTemplate.create(
        id="company-website",
        label="{domain} website",
        source_type="website",
        url_template="{website}",
        source_family="owned_site",
        rationale="Monitor public product and positioning changes from {domain}.",
        default_limit=1,
        rank_score=0.35,
        options={"adapter": "static", "source_family": "owned_site"},
    ),
    SourceTemplate.create(
        id="company-changelog",
        label="{domain} changelog",
        source_type="changelog",
        url_template="{website}/changelog",
        source_family="owned_site",
        rationale="Track product changes that may respond to customer complaints from {domain}.",
        default_limit=5,
        rank_score=0.55,
        options={"adapter": "static", "source_family": "owned_site"},
    ),
    SourceTemplate.create(
        id="company-blog",
        label="{domain} blog",
        source_type="blog",
        url_template="{website}/blog",
        source_family="owned_site",
        rationale="Track product announcements and customer-facing roadmap signals from {domain}.",
        default_limit=10,
        rank_score=0.45,
        options={"adapter": "static", "source_family": "owned_site"},
    ),
    SourceTemplate.create(
        id="reddit-market-search",
        label="{market_name} Reddit mentions",
        source_type="reddit_search",
        url_template="https://www.reddit.com/search.json?q={market_query}&sort=new",
        source_family="social",
        rationale="Find recent market-level complaints and discussions about {market_name}.",
        default_limit=25,
        rank_score=0.7,
        options={"adapter": "json", "source_family": "social"},
    ),
    SourceTemplate.create(
        id="hackernews-market-search",
        label="{market_name} Hacker News mentions",
        source_type="hackernews_search",
        url_template=(
            "https://hn.algolia.com/api/v1/search_by_date"
            "?query={market_query}&tags=story"
        ),
        source_family="technical_forum",
        rationale="Find technical buyer and founder discussions about {market_name}.",
        default_limit=25,
        applicable_categories=["ai_tools", "b2b_saas", "devtools"],
        rank_score=0.68,
        options={"adapter": "json", "source_family": "technical_forum"},
    ),
)


def get_default_source_templates() -> list[SourceTemplate]:
    """Return code-defined MVP source templates."""
    return list(DEFAULT_SOURCE_TEMPLATES)

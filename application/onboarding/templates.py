"""Template markets seeded for every new user on first login."""
from __future__ import annotations

import uuid

from domain.market import Market

_TEMPLATES = [
    {
        "name": "AI Writing Tools",
        "description": "Pain patterns from users of AI writing assistants like Grammarly, Jasper, and Copy.ai.",
        "target_user": "Content creators, marketers, and writers using AI-assisted writing tools",
        "idea_prompt": "Find unmet needs and friction points that a focused AI writing tool could solve better than the incumbents.",
    },
    {
        "name": "No-Code / Low-Code Tools",
        "description": "Frustrations from builders using Webflow, Bubble, Zapier, and Make.",
        "target_user": "Non-technical founders and operators automating workflows without engineers",
        "idea_prompt": "Surface automation gaps and workflow limitations that small teams keep hitting.",
    },
    {
        "name": "Developer Tools",
        "description": "Developer pain from tools like GitHub, VS Code extensions, CI/CD platforms, and API tools.",
        "target_user": "Individual developers and small engineering teams building software products",
        "idea_prompt": "Identify workflow bottlenecks that a focused developer tool could eliminate.",
    },
]


def seed_template_markets(user_id: str, market_repo: object) -> None:
    """Create template markets for a new user. No-op if they already have markets."""
    existing = market_repo.list_markets(user_id=user_id)
    if existing:
        return
    markets = [
        Market.create(
            id=str(uuid.uuid4()),
            name=tmpl["name"],
            description=tmpl["description"],
            target_user=tmpl["target_user"],
            idea_prompt=tmpl["idea_prompt"],
            user_id=user_id,
        )
        for tmpl in _TEMPLATES
    ]
    market_repo.save_markets(markets)

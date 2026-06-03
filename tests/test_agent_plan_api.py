import asyncio

from api.routes.signals import (
    SignalApiDependencies,
    get_market_agent_plan,
    propose_market_agent_actions,
)
from domain.agent import AgentFollowUp
from domain.niche import NicheSource, UserNiche
from domain.user import User


def test_get_market_agent_plan_returns_proposed_actions() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)

    response = asyncio.run(
        get_market_agent_plan(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    assert response["actions"][0]["action_type"] == "answer_follow_up"
    assert response["actions"][0]["metadata"]["follow_up_id"] == "follow-up-1"


def test_propose_market_agent_actions_persists_without_duplicates() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)

    response = asyncio.run(
        propose_market_agent_actions(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )
    repeated_response = asyncio.run(
        propose_market_agent_actions(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    stored_actions = dependencies.agent_action_repository.list_agent_actions(
        user_niche_id="market-1",
    )
    assert response["actions"][0]["action_type"] == "answer_follow_up"
    assert repeated_response["actions"] == []
    assert len(stored_actions) == 1
    assert stored_actions[0].metadata["follow_up_id"] == "follow-up-1"


def _seed_market_with_follow_up(dependencies: SignalApiDependencies) -> None:
    user_niche = UserNiche.create(
        id="market-1",
        user_id="user-1",
        template_niche_id="niche-1",
        job="Build internal tools",
        buyer="Ops teams",
        category="devtools",
    )
    dependencies.user_niche_repository.save_user_niche(user_niche)
    dependencies.niche_source_repository.save_niche_sources(
        [
            NicheSource.create(
                id="source-1",
                niche_id="niche-1",
                locator="https://example.com/feed",
                source_type="web",
                source_family="forum",
                is_gate_free=True,
                health_status="active",
            )
        ]
    )
    dependencies.agent_follow_up_repository.save_agent_follow_up(
        AgentFollowUp.create(
            id="follow-up-1",
            user_niche_id="market-1",
            question="Why is this credible?",
        )
    )

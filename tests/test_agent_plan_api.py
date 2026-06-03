import asyncio

from api.routes.signals import (
    SignalApiDependencies,
    approve_market_agent_action,
    dismiss_market_agent_action,
    get_market_agent_plan,
    list_market_agent_actions,
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


def test_approve_market_agent_action_updates_status() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    propose_response = asyncio.run(
        propose_market_agent_actions(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )
    action_id = propose_response["actions"][0]["id"]

    response = asyncio.run(
        approve_market_agent_action(
            "market-1",
            action_id,
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    assert response["action"]["status"] == "approved"


def test_list_market_agent_actions_returns_stored_actions() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    asyncio.run(
        propose_market_agent_actions(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    response = asyncio.run(
        list_market_agent_actions(
            "market-1",
            status="proposed",
            action_type="answer_follow_up",
            limit=10,
            dependencies=dependencies,
            current_user=User(id="user-1", email="user@example.com"),
        )
    )

    assert len(response["actions"]) == 1
    assert response["actions"][0]["action_type"] == "answer_follow_up"


def test_dismiss_market_agent_action_updates_status() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    propose_response = asyncio.run(
        propose_market_agent_actions(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )
    action_id = propose_response["actions"][0]["id"]

    response = asyncio.run(
        dismiss_market_agent_action(
            "market-1",
            action_id,
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    assert response["action"]["status"] == "dismissed"


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

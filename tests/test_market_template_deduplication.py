import asyncio
import json
import unittest
from unittest.mock import patch

from api.routes.signals import (
    MarketRequest,
    SignalApiDependencies,
    apply_template,
    create_market,
    list_markets,
    list_templates,
)
from domain.niche import Niche, UserNiche
from domain.user import User


class FakeMarketSourceLLM:
    def __init__(self) -> None:
        self.calls = 0

    def generate_structured_response(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict | None = None,
    ) -> str:
        self.calls += 1
        if self.calls == 1:
            return json.dumps({"valid": True, "reason": ""})
        return json.dumps(
            {
                "sources": [
                    {
                        "locator": (
                            "https://hn.algolia.com/api/v1/search_by_date"
                            "?query=devtools"
                        ),
                        "source_type": "hackernews",
                        "source_family": "technical_forum",
                        "is_gate_free": True,
                    }
                ]
            }
        )


class MarketTemplateDeduplicationTest(unittest.TestCase):
    def test_applying_same_template_twice_returns_existing_market(self) -> None:
        dependencies = SignalApiDependencies()
        template = Niche.create(
            id="template-devtools",
            job="Build internal tools",
            buyer="Developer teams",
            category="devtools",
        )
        dependencies.niche_repository.save_niches([template])
        current_user = User(id="user-1", email="user@example.com")

        with patch("api.routes.signals._enqueue_pipeline") as enqueue_pipeline:
            first = asyncio.run(
                apply_template(
                    "template-devtools",
                    dependencies=dependencies,
                    current_user=current_user,
                )
            )
            second = asyncio.run(
                apply_template(
                    "template-devtools",
                    dependencies=dependencies,
                    current_user=current_user,
                )
            )

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(
            len(dependencies.user_niche_repository.list_user_niches("user-1")),
            1,
        )
        enqueue_pipeline.assert_called_once_with(first["id"])

    def test_list_markets_hides_existing_duplicate_template_niches(self) -> None:
        dependencies = SignalApiDependencies()
        current_user = User(id="user-1", email="user@example.com")
        dependencies.user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-one",
                user_id="user-1",
                job="Build internal tools",
                buyer="Developer teams",
                category="devtools",
                template_niche_id="template-devtools",
            )
        )
        dependencies.user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-two",
                user_id="user-1",
                job="Build internal tools",
                buyer="Developer teams",
                category="devtools",
                template_niche_id="template-devtools",
            )
        )

        response = asyncio.run(
            list_markets(dependencies=dependencies, current_user=current_user)
        )

        self.assertEqual(len(response["markets"]), 1)
        self.assertEqual(response["markets"][0]["id"], "market-one")

    def test_list_templates_excludes_templates_user_already_added(self) -> None:
        dependencies = SignalApiDependencies()
        current_user = User(id="user-1", email="user@example.com")
        dependencies.niche_repository.save_niches([
            Niche.create(
                id="template-devtools",
                job="Build internal tools",
                buyer="Developer teams",
                category="devtools",
            ),
            Niche.create(
                id="template-analytics",
                job="Measure product analytics",
                buyer="Product teams",
                category="data",
            ),
        ])
        dependencies.user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-one",
                user_id="user-1",
                job="Build internal tools",
                buyer="Developer teams",
                category="devtools",
                template_niche_id="template-devtools",
            )
        )

        response = asyncio.run(
            list_templates(dependencies=dependencies, current_user=current_user)
        )

        self.assertEqual(
            [template["id"] for template in response["templates"]],
            ["template-analytics"],
        )

    def test_list_markets_hides_existing_duplicate_custom_niches(self) -> None:
        dependencies = SignalApiDependencies()
        current_user = User(id="user-1", email="user@example.com")
        dependencies.user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-one",
                user_id="user-1",
                job="Build internal tools",
                buyer="Developer teams",
                category="devtools",
            )
        )
        dependencies.user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-two",
                user_id="user-1",
                job=" build   internal tools ",
                buyer="developer teams",
                category="DevTools",
            )
        )

        response = asyncio.run(
            list_markets(dependencies=dependencies, current_user=current_user)
        )

        self.assertEqual(len(response["markets"]), 1)
        self.assertEqual(response["markets"][0]["id"], "market-one")

    def test_creating_same_custom_niche_twice_returns_existing_market(self) -> None:
        dependencies = SignalApiDependencies()
        current_user = User(id="user-1", email="user@example.com")
        request = MarketRequest(
            name="Build internal tools",
            target_user="Developer teams",
            description="devtools",
        )

        with patch("api.routes.signals._enqueue_pipeline") as enqueue_pipeline:
            first = asyncio.run(
                create_market(
                    request,
                    dependencies=dependencies,
                    current_user=current_user,
                )
            )
            second = asyncio.run(
                create_market(
                    request,
                    dependencies=dependencies,
                    current_user=current_user,
                )
            )

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(
            len(dependencies.user_niche_repository.list_user_niches("user-1")),
            1,
        )
        enqueue_pipeline.assert_called_once_with(first["id"])

    def test_custom_market_generated_sources_use_user_source_bindings(self) -> None:
        dependencies = SignalApiDependencies(llm_client=FakeMarketSourceLLM())
        current_user = User(id="user-1", email="user@example.com")

        with patch("api.routes.signals._enqueue_pipeline"):
            response = asyncio.run(
                create_market(
                    MarketRequest(
                        name="Build internal tools",
                        target_user="Developer teams",
                        description="devtools",
                    ),
                    dependencies=dependencies,
                    current_user=current_user,
                )
            )

        user_niche = dependencies.user_niche_repository.get_user_niche(response["id"])
        self.assertIsNotNone(user_niche)
        assert user_niche is not None
        canonical_source = dependencies.source_repository.get_source_by_identity(
            "hackernews",
            "https://hn.algolia.com/api/v1/search_by_date?query=devtools",
        )
        self.assertIsNotNone(canonical_source)
        assert canonical_source is not None
        user_source = dependencies.user_source_repository.get_user_source(
            user_niche.id,
            canonical_source.id,
        )
        self.assertIsNotNone(user_source)
        self.assertEqual(
            dependencies.source_repository.list_sources(
                source_type="hackernews",
            ),
            [canonical_source],
        )


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from unittest.mock import patch

from workers.seed_competitor_source import main, seed_competitor_source


class FakeRepository:
    saved_competitors = []
    saved_sources = []
    closed_count = 0

    def __init__(self, database_url: str):
        self.database_url = database_url

    def save_competitors(self, competitors):
        self.__class__.saved_competitors.extend(competitors)
        return len(competitors)

    def save_monitored_sources(self, sources):
        self.__class__.saved_sources.extend(sources)
        return len(sources)

    def close(self):
        self.__class__.closed_count += 1


class SeedCompetitorSourceTests(unittest.TestCase):
    def setUp(self):
        FakeRepository.saved_competitors = []
        FakeRepository.saved_sources = []
        FakeRepository.closed_count = 0

    def test_seeds_competitor_and_monitored_source(self):
        with (
            patch(
                "workers.seed_competitor_source.PostgresCompetitorRepository",
                FakeRepository,
            ),
            patch(
                "workers.seed_competitor_source.PostgresMonitoredSourceRepository",
                FakeRepository,
            ),
        ):
            result = seed_competitor_source(
                competitor_id="acme",
                competitor_name="Acme CRM",
                website="https://acme.example",
                category="crm",
                source_url="https://acme.example/reviews",
                source_type="reviews",
                limit=25,
                database_url="postgresql://localhost/lidscout",
            )

        self.assertEqual(result["competitor_inserted_count"], 1)
        self.assertEqual(result["source_inserted_count"], 1)
        self.assertEqual(FakeRepository.saved_competitors[0].id, "acme")
        self.assertEqual(FakeRepository.saved_sources[0].competitor_id, "acme")
        self.assertEqual(FakeRepository.saved_sources[0].limit, 25)
        self.assertEqual(FakeRepository.closed_count, 2)

    def test_rejects_non_postgres_database_url(self):
        with self.assertRaises(ValueError):
            seed_competitor_source(
                competitor_id="acme",
                competitor_name="Acme CRM",
                source_url="https://acme.example/reviews",
                database_url="sqlite:///lidscout.db",
            )

    def test_main_prints_seed_result(self):
        with (
            patch(
                "workers.seed_competitor_source.PostgresCompetitorRepository",
                FakeRepository,
            ),
            patch(
                "workers.seed_competitor_source.PostgresMonitoredSourceRepository",
                FakeRepository,
            ),
            patch("workers.seed_competitor_source.get_app_config") as get_app_config,
            patch("builtins.print") as print_call,
        ):
            get_app_config.return_value.DATABASE_URL = "postgresql://localhost/lidscout"
            exit_code = main(
                [
                    "--competitor-id",
                    "acme",
                    "--competitor-name",
                    "Acme CRM",
                    "--source-url",
                    "https://acme.example/reviews",
                ]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(print_call.call_args.args[0])
        self.assertEqual(payload["competitor"]["id"], "acme")
        self.assertEqual(payload["source"]["locator"], "https://acme.example/reviews")


if __name__ == "__main__":
    unittest.main()

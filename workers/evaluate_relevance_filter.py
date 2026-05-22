"""CLI runner for relevance-filter eval fixtures."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from application.extraction import RuleBasedRelevanceFilter
from application.extraction.relevance_eval import (
    evaluate_relevance_filter,
    load_labeled_relevance_examples,
)


DEFAULT_FIXTURE = Path("tests/fixtures/relevance_eval.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the rule-based relevance filter against labels.",
    )
    parser.add_argument(
        "--fixture",
        default=str(DEFAULT_FIXTURE),
        help="Path to a relevance eval JSON fixture.",
    )
    args = parser.parse_args(argv)

    examples = load_labeled_relevance_examples(args.fixture)
    report = evaluate_relevance_filter(RuleBasedRelevanceFilter(), examples)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 1 if report.mistakes else 0


if __name__ == "__main__":
    raise SystemExit(main())

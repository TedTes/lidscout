"""CLI runner for adaptive agent behavior eval fixtures."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from application.agent import rank_opportunities_with_feedback
from application.agent.evaluation import (
    evaluate_agent_ranker,
    load_labeled_agent_ranking_examples,
)


DEFAULT_FIXTURE = Path("tests/fixtures/agent_behavior_eval.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate feedback-aware opportunity ranking against labels.",
    )
    parser.add_argument(
        "--fixture",
        default=str(DEFAULT_FIXTURE),
        help="Path to an agent behavior eval JSON fixture.",
    )
    args = parser.parse_args(argv)

    examples = load_labeled_agent_ranking_examples(args.fixture)
    report = evaluate_agent_ranker(rank_opportunities_with_feedback, examples)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 1 if report.mistakes else 0


if __name__ == "__main__":
    raise SystemExit(main())

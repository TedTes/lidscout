"""CLI runner for opportunity qualification QA fixtures."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from application.opportunity import (
    OpportunitySynthesisContext,
    evaluate_opportunity_qualification,
)
from domain.cluster import SignalCluster
from domain.signal import Signal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate opportunity qualification thresholds against a fixture.",
    )
    parser.add_argument(
        "fixture",
        help="Path to a JSON fixture containing clusters and signals.",
    )
    parser.add_argument(
        "--minimum-average-score",
        type=float,
        default=7.0,
        help="Minimum cluster average score considered for opportunity synthesis.",
    )
    args = parser.parse_args(argv)

    payload = json.loads(Path(args.fixture).read_text())
    clusters = [_cluster_from_dict(item) for item in payload.get("clusters", [])]
    signals = [_signal_from_dict(item) for item in payload.get("signals", [])]
    context = _context_from_dict(payload.get("context"))
    report = evaluate_opportunity_qualification(
        clusters,
        signals,
        context=context,
        minimum_average_score=args.minimum_average_score,
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 1 if report.rejected_count or report.missing_signal_count else 0


def _cluster_from_dict(payload: dict[str, Any]) -> SignalCluster:
    return SignalCluster.create(
        id=str(payload["id"]),
        theme=str(payload["theme"]),
        summary=str(payload["summary"]),
        signal_ids=[str(item) for item in payload.get("signal_ids", [])],
        frequency=int(payload.get("frequency", len(payload.get("signal_ids", [])))),
        average_score=float(payload.get("average_score", 0.0)),
        top_examples=[
            str(item)
            for item in payload.get("top_examples", [])
        ],
    )


def _signal_from_dict(payload: dict[str, Any]) -> Signal:
    return Signal.create(
        id=str(payload["id"]),
        post_id=str(payload["post_id"]),
        pain=str(payload["pain"]),
        user_type=payload.get("user_type"),
        job_to_be_done=payload.get("job_to_be_done"),
        current_workaround=payload.get("current_workaround"),
        urgency=str(payload.get("urgency", "low")),
        severity=str(payload.get("severity", "low")),
        willingness_to_pay=payload.get("willingness_to_pay"),
        category=payload.get("category"),
        confidence=float(payload.get("confidence", 0.0)),
        niche_company_id=payload.get("niche_company_id"),
        niche_id=payload.get("niche_id"),
        evidence_url=payload.get("evidence_url"),
        evidence_text=payload.get("evidence_text"),
    )


def _context_from_dict(payload: dict[str, Any] | None) -> OpportunitySynthesisContext | None:
    if not payload:
        return None
    return OpportunitySynthesisContext(
        niche_name=payload.get("niche_name"),
        target_user=payload.get("target_user"),
        objective=payload.get("objective"),
        extra_instructions=payload.get("extra_instructions"),
        ignored_themes=payload.get("ignored_themes"),
        ignored_categories=payload.get("ignored_categories"),
    )


if __name__ == "__main__":
    raise SystemExit(main())

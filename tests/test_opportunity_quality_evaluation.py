import json
from pathlib import Path

from application.opportunity import evaluate_opportunity_qualification
from domain.cluster import SignalCluster
from domain.signal import Signal
from workers.evaluate_opportunity_quality import main


def test_evaluates_opportunity_qualification_thresholds() -> None:
    qualified_cluster = SignalCluster.create(
        id="cluster-qualified",
        theme="Reporting exports",
        summary="Finance teams struggle with reporting exports.",
        signal_ids=["signal-1", "signal-2"],
        frequency=2,
        average_score=8.2,
    )
    rejected_cluster = SignalCluster.create(
        id="cluster-rejected",
        theme="Single weak complaint",
        summary="One user mentioned a minor complaint.",
        signal_ids=["signal-3"],
        frequency=1,
        average_score=8.0,
    )
    skipped_cluster = SignalCluster.create(
        id="cluster-skipped",
        theme="Low score",
        summary="Low-scoring theme.",
        signal_ids=["signal-4"],
        frequency=1,
        average_score=4.0,
    )
    signals = [
        Signal.create(
            id="signal-1",
            post_id="post-1",
            pain="Exports take too long for finance teams.",
            user_type="finance teams",
            current_workaround="spreadsheets",
            urgency="high",
            severity="high",
            willingness_to_pay=True,
            confidence=0.82,
            niche_company_id="company-1",
            evidence_url="https://github.com/example/issues/1",
        ),
        Signal.create(
            id="signal-2",
            post_id="post-2",
            pain="Reporting exports break every week.",
            user_type="finance teams",
            current_workaround="manual CSV cleanup",
            urgency="high",
            severity="medium",
            willingness_to_pay=True,
            confidence=0.78,
            niche_company_id="company-2",
            evidence_url="https://stackoverflow.com/questions/1",
        ),
        Signal.create(
            id="signal-3",
            post_id="post-3",
            pain="Minor annoyance.",
            confidence=0.8,
            evidence_url="https://example.com/post",
        ),
    ]

    report = evaluate_opportunity_qualification(
        [qualified_cluster, rejected_cluster, skipped_cluster],
        signals,
    )

    assert report.qualified_count == 1
    assert report.rejected_count == 1
    assert report.skipped_low_score_count == 1
    assert report.rejection_reasons == {"insufficient_evidence": 1}


def test_opportunity_quality_cli_reports_fixture(tmp_path: Path, capsys) -> None:
    fixture = tmp_path / "opportunity_quality.json"
    fixture.write_text(
        json.dumps(
            {
                "clusters": [
                    {
                        "id": "cluster-1",
                        "theme": "Reporting exports",
                        "summary": "Teams struggle with exports.",
                        "signal_ids": ["signal-1"],
                        "frequency": 1,
                        "average_score": 8.0,
                    }
                ],
                "signals": [
                    {
                        "id": "signal-1",
                        "post_id": "post-1",
                        "pain": "Exports are slow.",
                        "confidence": 0.7,
                    }
                ],
            }
        )
    )

    exit_code = main([str(fixture)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["rejected_count"] == 1
    assert output["rejection_reasons"] == {"insufficient_evidence": 1}

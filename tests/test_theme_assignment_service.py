import json

from application.theme_memory import ThemeAssignmentService
from domain.finding import Finding
from domain.theme import Theme
from infrastructure.llm import LLMClient


class FakeLLMClient(LLMClient):
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[tuple[str, str, dict | None]] = []

    def generate_structured_response(
        self,
        prompt: str,
        content: str,
        schema: dict | None = None,
    ) -> str:
        self.calls.append((prompt, content, schema))
        return json.dumps(self.payload)


def _finding(*, embedding: list[float]) -> Finding:
    return Finding.create(
        id="349d4322-1614-48c1-a7d3-b50b3821a27c",
        user_niche_id="8de09fb9-75d0-40d5-b3ea-703ffea6a853",
        post_id="post-1",
        pain="Incremental models break on schema changes",
        evidence_text="dbt incremental models break on schema changes",
        structured_embedding_text="Incremental models break on schema changes",
        urgency="high",
        severity="medium",
        confidence=0.8,
        source_id="a815ccce-9fec-4528-8d9f-946c2d42ac29",
        category="data reliability",
        embedding=embedding,
    )


def _theme(*, embedding: list[float]) -> Theme:
    return Theme.create(
        id="c9158d97-9449-4bf2-9ef5-17bb825d522f",
        user_niche_id="8de09fb9-75d0-40d5-b3ea-703ffea6a853",
        title="Schema change reliability",
        summary="Analytics engineers need safer schema changes.",
        centroid_embedding=embedding,
    )


def test_assigns_high_confidence_without_llm():
    llm = FakeLLMClient({"same_unmet_need": False, "reason": "no"})
    result = ThemeAssignmentService(llm_client=llm).assign(
        _finding(embedding=[1.0, 0.0]),
        [_theme(embedding=[0.99, 0.01])],
    )

    assert result.created_theme is False
    assert result.assignment.assignment_method == "auto_high_confidence"
    assert llm.calls == []


def test_uses_llm_for_borderline_match():
    llm = FakeLLMClient({"same_unmet_need": True, "reason": "same workflow gap"})
    result = ThemeAssignmentService(llm_client=llm).assign(
        _finding(embedding=[1.0, 0.0]),
        [_theme(embedding=[0.75, 0.66])],
    )

    assert result.created_theme is False
    assert result.llm_evaluated is True
    assert result.assignment.assignment_method == "auto_borderline_llm"
    assert result.assignment.llm_decision == {
        "same_unmet_need": True,
        "reason": "same workflow gap",
    }
    assert len(llm.calls) == 1
    assert "same vendor" in llm.calls[0][0]


def test_creates_seed_theme_when_borderline_llm_rejects():
    llm = FakeLLMClient({"same_unmet_need": False, "reason": "different pain"})
    result = ThemeAssignmentService(llm_client=llm).assign(
        _finding(embedding=[1.0, 0.0]),
        [_theme(embedding=[0.75, 0.66])],
    )

    assert result.created_theme is True
    assert result.llm_evaluated is True
    assert result.theme.title == "data reliability"
    assert result.assignment.assignment_method == "seed_new_theme"


def test_creates_seed_theme_when_no_embedding():
    finding = _finding(embedding=[1.0, 0.0])
    finding = Finding.create(
        id=finding.id,
        user_niche_id=finding.user_niche_id,
        post_id=finding.post_id,
        pain=finding.pain,
        evidence_text=finding.evidence_text,
        structured_embedding_text=finding.structured_embedding_text,
        urgency=finding.urgency,
        severity=finding.severity,
        confidence=finding.confidence,
        category=finding.category,
    )

    result = ThemeAssignmentService().assign(finding, [_theme(embedding=[1.0, 0.0])])

    assert result.created_theme is True
    assert result.theme.centroid_embedding is None

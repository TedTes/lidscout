"""Assign accumulated findings to durable themes."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math

from domain.finding import Finding
from domain.theme import Theme, ThemeFinding
from infrastructure.llm import LLMClient


THEME_ASSIGNMENT_PROMPT = """
Decide whether a new finding describes the same unmet need as an existing theme.

Return JSON only:
- same_unmet_need: boolean
- reason: short string

Say true only when the buyer pain, desired outcome, and product/workflow gap are
substantially the same. Do not say true merely because the finding mentions the
same vendor, same broad category, or same technical topic.
""".strip()

THEME_ASSIGNMENT_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["same_unmet_need", "reason"],
    "properties": {
        "same_unmet_need": {"type": "boolean"},
        "reason": {"type": "string"},
    },
}


@dataclass(frozen=True)
class ThemeAssignmentResult:
    """Decision from assigning one finding into theme memory."""

    theme: Theme | None
    assignment: ThemeFinding | None
    created_theme: bool
    llm_evaluated: bool = False

    @property
    def is_assigned(self) -> bool:
        return self.assignment is not None


class ThemeAssignmentService:
    """Assigns findings to existing themes or creates seed themes."""

    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        high_confidence_threshold: float = 0.82,
        borderline_threshold: float = 0.70,
        max_borderline_candidates: int = 3,
    ):
        if not 0 <= borderline_threshold <= high_confidence_threshold <= 1:
            raise ValueError("theme assignment thresholds must be ordered within 0..1")
        if max_borderline_candidates < 1:
            raise ValueError("max_borderline_candidates must be at least 1")
        self.llm_client = llm_client
        self.high_confidence_threshold = high_confidence_threshold
        self.borderline_threshold = borderline_threshold
        self.max_borderline_candidates = max_borderline_candidates

    def assign(
        self,
        finding: Finding,
        themes: list[Theme],
        *,
        create_seed: bool = True,
    ) -> ThemeAssignmentResult:
        """Assign one finding to an existing theme.

        When create_seed=False, returns an unassigned result instead of
        immediately creating a singleton seed theme. The caller is then
        responsible for clustering unassigned findings together.
        """
        if not finding.embedding:
            return self._create_seed_theme(finding) if create_seed else _unassigned()

        candidates = self._rank_candidates(finding, themes)
        for theme, similarity in candidates:
            if similarity >= self.high_confidence_threshold:
                return ThemeAssignmentResult(
                    theme=theme,
                    assignment=ThemeFinding.create(
                        theme_id=theme.id,
                        finding_id=finding.id,
                        assignment_method="auto_high_confidence",
                        similarity_score=round(similarity, 4),
                    ),
                    created_theme=False,
                )

        borderline = [
            (theme, similarity)
            for theme, similarity in candidates
            if similarity >= self.borderline_threshold
        ][: self.max_borderline_candidates]
        for theme, similarity in borderline:
            decision = self._evaluate_borderline_match(finding, theme)
            if decision.get("same_unmet_need") is True:
                return ThemeAssignmentResult(
                    theme=theme,
                    assignment=ThemeFinding.create(
                        theme_id=theme.id,
                        finding_id=finding.id,
                        assignment_method="auto_borderline_llm",
                        similarity_score=round(similarity, 4),
                        llm_decision=decision,
                    ),
                    created_theme=False,
                    llm_evaluated=True,
                )

        if create_seed:
            return self._create_seed_theme(finding, llm_evaluated=bool(borderline))
        return _unassigned(llm_evaluated=bool(borderline))

    def cluster_unassigned(
        self,
        findings: list[Finding],
        *,
        threshold: float = 0.75,
    ) -> list[ThemeAssignmentResult]:
        """Cluster unassigned findings among themselves.

        Findings with mutual similarity >= threshold form a shared seed theme.
        Singletons (no match) are dropped — they remain in the findings table
        without a theme assignment until future runs accumulate more evidence.
        Returns one ThemeAssignmentResult per finding that joined a cluster.
        """
        if not findings:
            return []

        # Build connected components via pairwise cosine similarity.
        n = len(findings)
        component: list[int] = list(range(n))

        def root(i: int) -> int:
            while component[i] != i:
                component[i] = component[component[i]]
                i = component[i]
            return i

        def union(i: int, j: int) -> None:
            component[root(i)] = root(j)

        for i in range(n):
            if not findings[i].embedding:
                continue
            for j in range(i + 1, n):
                if not findings[j].embedding:
                    continue
                sim = _cosine_similarity(findings[i].embedding, findings[j].embedding)
                if sim >= threshold:
                    union(i, j)

        # Group by root into clusters; discard singletons.
        groups: dict[int, list[int]] = {}
        for i in range(n):
            r = root(i)
            groups.setdefault(r, []).append(i)
        clusters = [idxs for idxs in groups.values() if len(idxs) >= 2]

        results: list[ThemeAssignmentResult] = []
        for idxs in clusters:
            members = [findings[i] for i in idxs]
            theme = _seed_theme_for_cluster(members)
            for finding in members:
                results.append(
                    ThemeAssignmentResult(
                        theme=theme,
                        assignment=ThemeFinding.create(
                            theme_id=theme.id,
                            finding_id=finding.id,
                            assignment_method="seed_new_theme",
                            similarity_score=None,
                        ),
                        created_theme=True,
                    )
                )
        return results

    def _rank_candidates(
        self,
        finding: Finding,
        themes: list[Theme],
    ) -> list[tuple[Theme, float]]:
        ranked: list[tuple[Theme, float]] = []
        for theme in themes:
            if not theme.centroid_embedding:
                continue
            ranked.append(
                (
                    theme,
                    _cosine_similarity(finding.embedding or [], theme.centroid_embedding),
                )
            )
        return sorted(ranked, key=lambda item: item[1], reverse=True)

    def _evaluate_borderline_match(
        self,
        finding: Finding,
        theme: Theme,
    ) -> dict[str, object]:
        if self.llm_client is None:
            return {"same_unmet_need": False, "reason": "llm_not_configured"}
        raw_json = self.llm_client.generate_structured_response(
            THEME_ASSIGNMENT_PROMPT,
            _assignment_prompt_content(finding, theme),
            THEME_ASSIGNMENT_RESPONSE_SCHEMA,
        )
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            return {"same_unmet_need": False, "reason": "invalid_llm_json"}
        return {
            "same_unmet_need": bool(payload.get("same_unmet_need")),
            "reason": str(payload.get("reason") or "").strip() or "no_reason",
        }

    def _create_seed_theme(
        self,
        finding: Finding,
        *,
        llm_evaluated: bool = False,
    ) -> ThemeAssignmentResult:
        theme = Theme.create(
            user_niche_id=finding.user_niche_id,
            niche_id=finding.niche_id,
            title=_theme_title_for(finding),
            summary=finding.pain,
            finding_count=1,
            source_count=1 if finding.source_id else 0,
            company_count=1 if finding.company_id else 0,
            average_confidence=finding.confidence,
            latest_finding_at=finding.detected_at or finding.extracted_at,
            centroid_embedding=finding.embedding,
            metadata={"seed_finding_id": finding.id},
        )
        return ThemeAssignmentResult(
            theme=theme,
            assignment=ThemeFinding.create(
                theme_id=theme.id,
                finding_id=finding.id,
                assignment_method="seed_new_theme",
                similarity_score=None,
            ),
            created_theme=True,
            llm_evaluated=llm_evaluated,
        )


def _unassigned(*, llm_evaluated: bool = False) -> ThemeAssignmentResult:
    return ThemeAssignmentResult(
        theme=None,
        assignment=None,
        created_theme=False,
        llm_evaluated=llm_evaluated,
    )


def _seed_theme_for_cluster(findings: list[Finding]) -> Theme:
    """Create a seed theme whose centroid is the average of member embeddings."""
    anchor = findings[0]
    title = _theme_title_for(anchor)
    summary = anchor.pain

    embeddings = [f.embedding for f in findings if f.embedding]
    centroid: list[float] | None = None
    if embeddings:
        dim = len(embeddings[0])
        centroid = [
            sum(emb[d] for emb in embeddings) / len(embeddings)
            for d in range(dim)
        ]

    source_ids = {f.source_id for f in findings if f.source_id}
    company_ids = {f.company_id for f in findings if f.company_id}
    confidences = [f.confidence for f in findings]
    timestamps = [
        t for f in findings
        for t in [f.detected_at or f.extracted_at]
        if t is not None
    ]

    return Theme.create(
        user_niche_id=anchor.user_niche_id,
        niche_id=anchor.niche_id,
        title=title,
        summary=summary,
        finding_count=len(findings),
        source_count=len(source_ids),
        company_count=len(company_ids),
        average_confidence=sum(confidences) / len(confidences),
        latest_finding_at=max(timestamps) if timestamps else None,
        centroid_embedding=centroid,
        metadata={"seed_finding_ids": [f.id for f in findings]},
    )


def _assignment_prompt_content(finding: Finding, theme: Theme) -> str:
    return "\n".join(
        [
            "Existing theme:",
            f"title: {theme.title}",
            f"summary: {theme.summary}",
            f"metadata: {json.dumps(theme.metadata, sort_keys=True)}",
            "",
            "New finding:",
            f"pain: {finding.pain}",
            f"affected_user: {finding.affected_user or ''}",
            f"job_to_be_done: {finding.job_to_be_done or ''}",
            f"current_workaround: {finding.current_workaround or ''}",
            f"category: {finding.category or ''}",
            f"evidence_text: {finding.evidence_text}",
        ]
    )


def _theme_title_for(finding: Finding) -> str:
    if finding.category:
        return finding.category.strip()[:80]
    return finding.pain.strip()[:80]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return sum(left_value * right_value for left_value, right_value in zip(left, right)) / (
        left_norm * right_norm
    )

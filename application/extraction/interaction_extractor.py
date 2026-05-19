"""
Public interaction extraction application service.

This orchestrates ingestion, rule detection, and signal clustering:
1. Normalize each public page or pasted text source into page JSON.
2. Extract public comments/review snippets.
3. Classify comments using the domain signal detector.
4. Cluster recurring negative signals using the domain clusterer.
"""
import re
from typing import Iterable, Optional

from api.schemas import (
    InteractionExtractionRequest,
    InteractionExtractionResponse,
    NegativeSignal,
    PublicInteraction,
)
from application.ingestion.page_extractor import PageDocument, PageExtractorService
from application.interfaces import IInteractionExtractionService
from domain.cluster.negative_signal_clusterer import NegativeSignalClusterer
from domain.signal.detector import SignalRuleDetector
from domain.signal.taxonomy import REVIEW_LABELS


class InteractionExtractorService(IInteractionExtractionService):
    """Extracts comments and negative signals from review pages or pasted text."""

    def __init__(
        self,
        page_extractor: Optional[PageExtractorService] = None,
        signal_detector: Optional[SignalRuleDetector] = None,
        signal_clusterer: Optional[NegativeSignalClusterer] = None,
    ):
        self.page_extractor = page_extractor or PageExtractorService()
        self.signal_detector = signal_detector or SignalRuleDetector()
        self.signal_clusterer = signal_clusterer or NegativeSignalClusterer()

    async def extract(
        self,
        request: InteractionExtractionRequest,
    ) -> InteractionExtractionResponse:
        documents = []
        for index, source in enumerate(request.sources, start=1):
            documents.append(await self.page_extractor.extract(source, index))

        interactions = []
        for document in documents:
            interactions.extend(self._extract_interactions(document))

        negative_comments = [
            interaction
            for interaction in interactions
            if interaction.sentiment in {"negative", "mixed"}
        ]
        negative_signals = self._build_negative_signals(negative_comments)

        return InteractionExtractionResponse(
            total_sources=len(documents),
            pages=[document.page for document in documents],
            interactions=interactions,
            negative_comments=negative_comments,
            negative_signals=negative_signals,
        )

    def _extract_interactions(self, document: PageDocument) -> list[PublicInteraction]:
        candidates = self._comment_candidates(document.text)
        interactions = []

        for candidate in candidates:
            body = self._clean_comment(candidate)
            if not self._is_useful_comment(body):
                continue

            sentiment, evidence_terms = self.signal_detector.classify_sentiment(body)
            topics = self.signal_detector.classify_topics(body)
            interactions.append(
                PublicInteraction(
                    interaction_id=f"{document.page.source_id}-interaction-{len(interactions) + 1}",
                    source_id=document.page.source_id,
                    body=body,
                    rating=self._extract_rating(candidate),
                    sentiment=sentiment,
                    topics=topics,
                    evidence_terms=evidence_terms,
                )
            )

        return interactions

    def _comment_candidates(self, text: str) -> list[str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        candidates = []

        for index, line in enumerate(lines):
            lower = line.lower()
            if self._looks_like_labelled_review_line(lower):
                candidate = line
                if self._ends_with_label(lower) and index + 1 < len(lines):
                    candidate = f"{line} {lines[index + 1]}"
                candidates.append(candidate)

        quoted = re.findall(r"[\"“]([^\"”]{40,600})[\"”]", text)
        candidates.extend(quoted)

        if not candidates:
            candidates.extend(self._sentiment_sentences(text))

        return self._dedupe(candidates)

    def _looks_like_labelled_review_line(self, line_lower: str) -> bool:
        if any(line_lower.startswith(f"{label}:") for label in REVIEW_LABELS):
            return True
        if any(label in line_lower[:80] for label in REVIEW_LABELS):
            return True
        return self.signal_detector.has_sentiment_terms(line_lower)

    def _ends_with_label(self, line_lower: str) -> bool:
        return any(line_lower.rstrip(":") == label for label in REVIEW_LABELS)

    def _sentiment_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        return [
            sentence
            for sentence in sentences
            if 35 <= len(sentence.strip()) <= 700
            and self.signal_detector.has_sentiment_terms(sentence.lower())
        ]

    def _clean_comment(self, comment: str) -> str:
        cleaned = re.sub(r"\s+", " ", comment).strip()
        cleaned = re.sub(
            r"^(pros|cons|overall|review)\s*:\s*",
            lambda match: f"{match.group(1).title()}: ",
            cleaned,
            flags=re.I,
        )
        return cleaned[:1200]

    def _is_useful_comment(self, body: str) -> bool:
        if len(body) < 25:
            return False
        boilerplate = ["cookie", "privacy policy", "terms of use", "sign in", "write a review"]
        return not any(term in body.lower() for term in boilerplate)

    def _extract_rating(self, text: str) -> Optional[float]:
        patterns = [
            r"(\d(?:\.\d)?)\s*(?:out of|/)\s*5",
            r"rating[:\s]+(\d(?:\.\d)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                value = float(match.group(1))
                if 0 <= value <= 5:
                    return value
        return None

    def _build_negative_signals(
        self,
        negative_comments: list[PublicInteraction],
    ) -> list[NegativeSignal]:
        return [
            NegativeSignal(
                theme=cluster.theme,
                frequency=cluster.frequency,
                severity=cluster.severity,
                interaction_ids=cluster.interaction_ids,
                excerpts=cluster.excerpts,
            )
            for cluster in self.signal_clusterer.cluster(negative_comments)
        ]

    def _dedupe(self, candidates: Iterable[str]) -> list[str]:
        seen = set()
        deduped = []
        for candidate in candidates:
            key = re.sub(r"\W+", "", candidate.lower())[:160]
            if key and key not in seen:
                seen.add(key)
                deduped.append(candidate)
        return deduped

"""Rule-based signal detector for public online activity text."""
import re
from typing import Literal

from domain.signal.taxonomy import NEGATIVE_THEMES, POSITIVE_TERMS

Sentiment = Literal["negative", "neutral", "positive", "mixed", "unknown"]


class SignalRuleDetector:
    """Classifies sentiment and topics from public activity text."""

    def __init__(
        self,
        negative_themes: dict[str, list[str]] | None = None,
        positive_terms: list[str] | None = None,
    ):
        self.negative_themes = negative_themes or NEGATIVE_THEMES
        self.positive_terms = positive_terms or POSITIVE_TERMS

    def has_sentiment_terms(self, text_lower: str) -> bool:
        """Return whether text contains any tracked positive or negative term."""
        return any(
            self.contains_keyword(text_lower, term)
            for term in self.negative_terms + self.positive_terms
        )

    def classify_sentiment(self, body: str) -> tuple[Sentiment, list[str]]:
        """Classify a text snippet and return supporting evidence terms."""
        lower = body.lower()
        negative_hits = [
            term for term in self.negative_terms if self.contains_keyword(lower, term)
        ]
        positive_hits = [
            term for term in self.positive_terms if self.contains_keyword(lower, term)
        ]

        if negative_hits and positive_hits:
            return "mixed", negative_hits[:8]
        if negative_hits:
            return "negative", negative_hits[:8]
        if positive_hits:
            return "positive", positive_hits[:8]
        return "unknown", []

    def classify_topics(self, body: str) -> list[str]:
        """Return negative signal topics present in a text snippet."""
        lower = body.lower()
        topics = []
        for theme, terms in self.negative_themes.items():
            if any(self.contains_keyword(lower, term) for term in terms):
                topics.append(theme)
        return topics

    @property
    def negative_terms(self) -> list[str]:
        """Flattened negative term list."""
        return [term for terms in self.negative_themes.values() for term in terms]

    def contains_keyword(self, text_lower: str, keyword: str) -> bool:
        """Match keywords without partial word false positives."""
        pattern = rf"(?<![a-z0-9]){re.escape(keyword.lower())}(?![a-z0-9])"
        return bool(re.search(pattern, text_lower))

"""Rule taxonomy for public activity signal detection."""

NEGATIVE_THEMES: dict[str, list[str]] = {
    "pricing complaints": ["expensive", "overpriced", "cost", "price", "pricing", "too much"],
    "usability complaints": ["hard to use", "difficult", "confusing", "clunky", "not intuitive"],
    "setup or onboarding complaints": ["setup", "implementation", "onboarding", "training", "migration"],
    "support complaints": ["support", "customer service", "slow response", "unhelpful"],
    "bugs and reliability": ["bug", "buggy", "crash", "slow", "lag", "unreliable", "downtime"],
    "missing features": ["missing", "lack", "wish", "doesn't have", "does not have", "limited"],
    "integration complaints": ["integration", "integrate", "api", "sync", "zapier"],
    "reporting complaints": ["report", "reporting", "analytics", "dashboard", "export"],
    "mobile complaints": ["mobile", "app", "ios", "android"],
    "manual workflow complaints": ["manual", "spreadsheet", "copy and paste", "time consuming", "repetitive"],
}

POSITIVE_TERMS: list[str] = [
    "easy",
    "great",
    "helpful",
    "intuitive",
    "love",
    "reliable",
    "simple",
    "useful",
]

REVIEW_LABELS: list[str] = [
    "pros",
    "cons",
    "overall",
    "review",
    "what do you like",
    "what do you dislike",
    "reasons for switching",
    "recommendations to others",
]

"""Application-specific exceptions."""


class LidScoutError(Exception):
    """Base exception for expected LidScout failures."""


class IngestionError(LidScoutError):
    """Raised when an online source cannot be ingested."""


class ExtractionError(LidScoutError):
    """Raised when public activity cannot be extracted into signals."""

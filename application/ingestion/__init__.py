"""Source ingestion services and adapters."""
from application.ingestion.service import IngestionResult, IngestionService, RawPostRepository
from application.ingestion.source_resolver import (
    SourceAdapter,
    SourceFetchDetail,
    SourceFetchResult,
    SourceResolver,
)

__all__ = [
    "IngestionResult",
    "IngestionService",
    "RawPostRepository",
    "SourceAdapter",
    "SourceFetchDetail",
    "SourceFetchResult",
    "SourceResolver",
]

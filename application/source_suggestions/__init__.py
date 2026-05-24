"""Application service for competitor source suggestions."""
from application.source_suggestions.default_templates import (
    DEFAULT_SOURCE_TEMPLATES,
    get_default_source_templates,
)
from application.source_suggestions.service import (
    SourceSuggestion,
    SourceSuggestionService,
)
from application.source_suggestions.template_renderer import (
    render_source_candidate,
    render_source_candidates,
)

__all__ = [
    "DEFAULT_SOURCE_TEMPLATES",
    "SourceSuggestion",
    "SourceSuggestionService",
    "get_default_source_templates",
    "render_source_candidate",
    "render_source_candidates",
]

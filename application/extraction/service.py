"""Signal extraction service."""
import json
from dataclasses import dataclass
import logging

from domain.post import RawPost
from domain.signal import Signal
from infrastructure.llm import LLMClient
from shared.errors import ExtractionError
from shared.logger import get_logger, log_event


SIGNAL_EXTRACTION_PROMPT = (
    "Extract one market or pain signal from this post. "
    "Return only structured JSON with has_signal and optional signal fields."
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class SignalExtractionResult:
    """Result of extracting a signal candidate from a raw post."""

    post_id: str
    has_signal: bool
    signal: Signal | None = None


class ExtractionService:
    """Extracts structured signal candidates from raw posts using an LLM client."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def extract(self, post: RawPost) -> SignalExtractionResult:
        try:
            raw_json = self.llm_client.generate_structured_response(
                SIGNAL_EXTRACTION_PROMPT,
                self._post_content(post),
            )
            payload = self._parse_json(raw_json)

            if payload.get("has_signal") is False:
                return SignalExtractionResult(post_id=post.id, has_signal=False)

            if payload.get("has_signal") is not True:
                raise ExtractionError("Extraction JSON must include has_signal as a boolean")

            signal_payload = payload.get("signal")
            if not isinstance(signal_payload, dict):
                raise ExtractionError("Extraction JSON must include a signal object")

            try:
                signal = Signal.create(
                    id=signal_payload.get("id") or f"signal:{post.id}",
                    post_id=post.id,
                    pain=signal_payload.get("pain", ""),
                    user_type=signal_payload.get("user_type"),
                    job_to_be_done=signal_payload.get("job_to_be_done"),
                    current_workaround=signal_payload.get("current_workaround"),
                    urgency=signal_payload.get("urgency", "low"),
                    severity=signal_payload.get("severity", "low"),
                    willingness_to_pay=signal_payload.get("willingness_to_pay"),
                    category=signal_payload.get("category"),
                    confidence=signal_payload.get("confidence", 0.0),
                )
            except ValueError as exc:
                raise ExtractionError(str(exc)) from exc
        except Exception as exc:
            log_event(
                logger,
                "extraction_failed",
                level=logging.ERROR,
                post_id=post.id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise

        return SignalExtractionResult(
            post_id=post.id,
            has_signal=True,
            signal=signal,
        )

    def _parse_json(self, raw_json: str) -> dict:
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ExtractionError("LLM returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise ExtractionError("Extraction JSON must be an object")

        return payload

    def _post_content(self, post: RawPost) -> str:
        return "\n".join(
            [
                f"source: {post.source}",
                f"title: {post.title}",
                f"body: {post.body}",
            ]
        )

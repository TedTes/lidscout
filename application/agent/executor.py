"""Execution service for approved niche research agent actions."""
from dataclasses import dataclass
from dataclasses import replace

from application.ports import (
    AgentActionRepository,
    AgentAlertRepository,
    AgentFollowUpRepository,
    NicheSourceRepository,
    SourceRepository,
    UserSourceRepository,
)
from domain.agent import AgentAction
from domain.niche import NicheSource, UserSource
from domain.source import Source


@dataclass(frozen=True)
class AgentActionExecutionResult:
    """Summary of one agent action execution pass."""

    executed_count: int
    failed_count: int
    skipped_count: int


class AgentActionExecutor:
    """Apply approved agent actions to mutable system state."""

    def __init__(
        self,
        action_repository: AgentActionRepository,
        niche_source_repository: NicheSourceRepository | None = None,
        follow_up_repository: AgentFollowUpRepository | None = None,
        alert_repository: AgentAlertRepository | None = None,
        source_repository: SourceRepository | None = None,
        user_source_repository: UserSourceRepository | None = None,
    ) -> None:
        self._action_repository = action_repository
        self._niche_source_repository = niche_source_repository
        self._follow_up_repository = follow_up_repository
        self._alert_repository = alert_repository
        self._source_repository = source_repository
        self._user_source_repository = user_source_repository

    def execute_approved_actions(self, user_niche_id: str) -> AgentActionExecutionResult:
        """Execute approved actions for one niche agent."""
        actions = self._action_repository.list_agent_actions(
            user_niche_id=user_niche_id,
            status="approved",
            limit=100,
        )
        executed_count = 0
        failed_count = 0
        skipped_count = 0
        for action in actions:
            if action.action_type == "pause_source":
                if self._pause_source(action):
                    self._action_repository.update_agent_action_status(
                        action.id,
                        "completed",
                    )
                    executed_count += 1
                else:
                    self._action_repository.update_agent_action_status(
                        action.id,
                        "failed",
                    )
                    failed_count += 1
                continue
            if action.action_type == "answer_follow_up":
                if self._answer_follow_up(action):
                    self._action_repository.update_agent_action_status(
                        action.id,
                        "completed",
                    )
                    executed_count += 1
                else:
                    self._action_repository.update_agent_action_status(
                        action.id,
                        "failed",
                    )
                    failed_count += 1
                continue
            if action.action_type == "send_alert":
                if self._send_alert(action):
                    self._action_repository.update_agent_action_status(
                        action.id,
                        "completed",
                    )
                    executed_count += 1
                else:
                    self._action_repository.update_agent_action_status(
                        action.id,
                        "failed",
                    )
                    failed_count += 1
                continue
            if action.action_type == "suggest_source":
                if self._suggest_source(action):
                    self._action_repository.update_agent_action_status(
                        action.id,
                        "completed",
                    )
                    executed_count += 1
                else:
                    self._action_repository.update_agent_action_status(
                        action.id,
                        "failed",
                    )
                    failed_count += 1
                continue
            skipped_count += 1
        return AgentActionExecutionResult(
            executed_count=executed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
        )

    def _pause_source(self, action: AgentAction) -> bool:
        source_id = str(action.metadata.get("source_id") or "").strip()
        if not source_id:
            return False
        if self._pause_user_source(action.user_niche_id, source_id):
            return True
        if self._niche_source_repository is None:
            return False
        return self._niche_source_repository.update_niche_source_health(
            source_id,
            "paused",
        )

    def _pause_user_source(self, user_niche_id: str, source_id: str) -> bool:
        if self._user_source_repository is None:
            return False
        user_source = self._user_source_repository.get_user_source(
            user_niche_id,
            source_id,
        )
        if user_source is None:
            for candidate in self._user_source_repository.list_user_sources(
                user_niche_id,
                include_muted=True,
            ):
                if (
                    candidate.id == source_id
                    or candidate.template_source_binding_id == source_id
                ):
                    user_source = candidate
                    break
        if user_source is None:
            if (
                self._source_repository is None
                or self._source_repository.get_source(source_id) is None
            ):
                return False
            user_source = UserSource.create(
                user_niche_id=user_niche_id,
                source_id=source_id,
                enabled=False,
                muted=True,
            )
        else:
            user_source = replace(user_source, enabled=False, muted=True)
        self._user_source_repository.save_user_sources([user_source])
        saved = self._user_source_repository.get_user_source(
            user_source.user_niche_id,
            user_source.source_id,
        )
        return saved is not None and saved.muted and not saved.enabled

    def _answer_follow_up(self, action: AgentAction) -> bool:
        if self._follow_up_repository is None:
            return False
        follow_up_id = str(action.metadata.get("follow_up_id") or "").strip()
        response = str(action.metadata.get("response") or "").strip()
        if not follow_up_id or not response:
            return False
        updated = self._follow_up_repository.update_agent_follow_up(
            follow_up_id,
            status="answered",
            response=response,
            metadata={
                "answered_by_action_id": action.id,
                "answer_source": action.metadata.get("answer_source", "agent_action"),
            },
        )
        return updated is not None

    def _send_alert(self, action: AgentAction) -> bool:
        if self._alert_repository is None:
            return False
        alert_id = str(action.metadata.get("alert_id") or "").strip()
        if not alert_id:
            return False
        acknowledged = self._alert_repository.acknowledge_agent_alert(alert_id)
        return acknowledged is not None

    def _suggest_source(self, action: AgentAction) -> bool:
        user_source = self._user_source_from_action(action)
        if user_source is not None and self._user_source_repository is not None:
            self._user_source_repository.save_user_sources([user_source])
            return (
                self._user_source_repository.get_user_source(
                    user_source.user_niche_id,
                    user_source.source_id,
                )
                is not None
            )
        source = self._source_from_action(action)
        if source is None:
            return False
        if self._niche_source_repository is None:
            return False
        return self._niche_source_repository.save_niche_sources([source]) > 0

    def _user_source_from_action(self, action: AgentAction) -> UserSource | None:
        if self._source_repository is None or self._user_source_repository is None:
            return None
        locator = str(action.metadata.get("locator") or "").strip()
        source_type = str(action.metadata.get("source_type") or "").strip()
        source_family = str(action.metadata.get("source_family") or "").strip()
        if not locator or not source_type or not source_family:
            return None
        try:
            source = self._source_repository.get_source_by_identity(
                source_type,
                locator,
            )
            if source is None:
                source = Source.create(
                    id=str(action.metadata.get("source_id") or "").strip() or None,
                    locator=locator,
                    source_type=source_type,
                    source_family=source_family,
                    is_gate_free=bool(action.metadata.get("is_gate_free", False)),
                    access_mode=str(action.metadata.get("access_mode") or "unknown"),
                    requires_proxy=bool(action.metadata.get("requires_proxy", False)),
                    requires_auth=bool(action.metadata.get("requires_auth", False)),
                )
                self._source_repository.save_sources([source])
                source = (
                    self._source_repository.get_source_by_identity(
                        source.source_type,
                        source.locator,
                    )
                    or source
                )
            return UserSource.create(
                user_niche_id=action.user_niche_id,
                source_id=source.id,
                enabled=bool(action.metadata.get("enabled", True)),
                cadence=_clean_optional_metadata(
                    action.metadata.get("scan_frequency"),
                ),
                limit=_int_optional_metadata(action.metadata.get("limit")),
                options={
                    "created_by_action_id": action.id,
                    **dict(action.metadata.get("options") or {}),
                },
            )
        except (TypeError, ValueError):
            return None

    def _source_from_action(self, action: AgentAction) -> NicheSource | None:
        niche_id = str(action.metadata.get("niche_id") or "").strip()
        locator = str(action.metadata.get("locator") or "").strip()
        source_type = str(action.metadata.get("source_type") or "").strip()
        source_family = str(action.metadata.get("source_family") or "").strip()
        if not niche_id or not locator or not source_type or not source_family:
            return None
        try:
            return NicheSource.create(
                id=str(action.metadata.get("source_id") or "").strip() or None,
                niche_id=niche_id,
                locator=locator,
                source_type=source_type,
                source_family=source_family,
                is_gate_free=bool(action.metadata.get("is_gate_free", False)),
                company_id=_clean_optional_metadata(action.metadata.get("company_id")),
                enabled=bool(action.metadata.get("enabled", True)),
                limit=_int_optional_metadata(action.metadata.get("limit")),
                scan_frequency=_clean_optional_metadata(
                    action.metadata.get("scan_frequency"),
                ),
                buyer_voice_verified=bool(
                    action.metadata.get("buyer_voice_verified", False),
                ),
                tier=_int_optional_metadata(action.metadata.get("tier")),
                signal_quality_score=_float_optional_metadata(
                    action.metadata.get("signal_quality_score"),
                ),
                access_mode=str(action.metadata.get("access_mode") or "unknown"),
                requires_proxy=bool(action.metadata.get("requires_proxy", False)),
                requires_auth=bool(action.metadata.get("requires_auth", False)),
                recommended_cadence=_clean_optional_metadata(
                    action.metadata.get("recommended_cadence"),
                ),
                options={
                    "created_by_action_id": action.id,
                    **dict(action.metadata.get("options") or {}),
                },
            )
        except (TypeError, ValueError):
            return None


def _clean_optional_metadata(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _int_optional_metadata(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_optional_metadata(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

"""Execution service for approved niche research agent actions."""
from dataclasses import dataclass

from application.ports import (
    AgentActionRepository,
    AgentFollowUpRepository,
    NicheSourceRepository,
)
from domain.agent import AgentAction


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
        niche_source_repository: NicheSourceRepository,
        follow_up_repository: AgentFollowUpRepository | None = None,
    ) -> None:
        self._action_repository = action_repository
        self._niche_source_repository = niche_source_repository
        self._follow_up_repository = follow_up_repository

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
        return self._niche_source_repository.update_niche_source_health(
            source_id,
            "paused",
        )

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

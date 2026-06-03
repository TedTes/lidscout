"""Execution service for approved niche research agent actions."""
from dataclasses import dataclass

from application.ports import AgentActionRepository, NicheSourceRepository
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
    ) -> None:
        self._action_repository = action_repository
        self._niche_source_repository = niche_source_repository

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

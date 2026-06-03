# Claude Code Prompt: Agent Action Review UI

You are improving the LidScout web client. Focus on product flow and information hierarchy, not visual restyling. Keep the current visual language unless a layout adjustment is required.

## Goal

Make the agent feel like it proposes useful next steps that the user can approve, dismiss, and execute without exposing backend plumbing.

The user should understand:

1. What the agent wants to do next.
2. Why it wants to do it.
3. What will change if they approve it.
4. Whether the action completed or failed.

## Backend APIs

Use the existing API client or add typed methods for:

- `GET /markets/{market_id}/agent/actions`
- `POST /markets/{market_id}/agent/actions/plan`
- `POST /markets/{market_id}/agent/actions/{action_id}/approve`
- `POST /markets/{market_id}/agent/actions/{action_id}/dismiss`
- `POST /markets/{market_id}/agent/actions/execute`

Action shape:

- `id`
- `market_id`
- `action_type`
- `status`
- `reason`
- `metadata`
- `created_at`
- `completed_at`

Supported action types:

- `pause_source`
- `suggest_source`
- `answer_follow_up`
- `send_alert`
- `wait`

## Placement

Add this as a secondary surface in the selected market workspace, not top-level navigation.

Recommended placement:

- A compact "Agent actions" section on the Activity page.
- Optionally a small action count indicator near the Activity tab when proposed actions exist.
- Do not add another persistent sidebar item.

## UX Behavior

Show action cards grouped by status:

- Proposed
- Approved
- Completed
- Failed
- Dismissed

Proposed actions should be the only group with primary controls:

- Approve
- Dismiss

Approved actions should show:

- "Ready to run"
- One "Run approved actions" button for the market, not one run button per card.

Completed and failed actions should be audit history only.

## Copy Guidelines

Translate backend action types into user-facing language:

- `pause_source`: "Pause noisy source"
- `suggest_source`: "Add source"
- `answer_follow_up`: "Answer follow-up"
- `send_alert`: "Send alert"
- `wait`: "No action needed"

Avoid user-facing labels like:

- `action_type`
- `metadata`
- `execute`
- `proposed status`

Use the action `reason` as the primary explanation. Use metadata only to add concise context:

- Source URL or source family for source actions
- Follow-up question for follow-up actions
- Alert title/severity for alert actions

## Safety

Actions that mutate state must be explicit:

- Pausing a source should say which source will be paused.
- Adding a source should show the locator and whether it requires auth/proxy.
- Answering a follow-up should show the prepared answer if present.
- Sending an alert should show which alert will be marked as delivered/acknowledged.

If required metadata is missing, show the action as incomplete and do not offer approval.

## Empty States

If there are no actions:

- Show a compact empty state: "No agent actions waiting."
- Provide a secondary "Check for next actions" button that calls `POST /markets/{market_id}/agent/actions/plan`.

If action planning returns none:

- Keep the empty state.
- Do not show a success toast that feels noisy.

## Loading/Error States

- Use inline loading on action buttons.
- Optimistically disable buttons while requests are in flight.
- On failure, keep the card visible and show a concise inline error.
- Refresh the action list after approve, dismiss, plan, and run-approved requests.

## Acceptance Criteria

- Proposed actions can be planned, approved, and dismissed from the UI.
- Approved actions can be run in one market-level operation.
- Completed/failed actions remain visible as history.
- The UI never exposes raw JSON metadata.
- Missing metadata prevents unsafe approval.
- The surface fits inside the existing Activity page without crowding the primary Gaps experience.

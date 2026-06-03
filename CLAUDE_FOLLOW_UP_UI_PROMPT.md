# Claude Code Prompt: Follow-Up Questions UI

You are improving the LidScout web client. Focus on the follow-up question workflow inside a selected market workspace. Keep the current visual system and avoid broad restyling.

## Goal

Let users ask the research agent follow-up questions about a gap, theme, or market, then see answers once the agent responds.

This should feel like a lightweight research thread, not a generic chatbot.

## Backend APIs

Use or add typed API client methods for:

- `GET /markets/{market_id}/agent/follow-ups`
- `POST /markets/{market_id}/agent/follow-ups`
- `POST /markets/{market_id}/agent/follow-ups/{follow_up_id}/answer`
- `POST /markets/{market_id}/agent/follow-ups/{follow_up_id}/dismiss`

Follow-up shape:

- `id`
- `market_id`
- `question`
- `opportunity_id`
- `cluster_id`
- `status`
- `response`
- `metadata`
- `created_at`
- `updated_at`

## Placement

Do not add a top-level nav item.

Recommended placements:

- On a gap card/detail surface: a compact “Ask follow-up” affordance.
- On the Activity page: a “Follow-ups” section showing queued, answered, and dismissed questions.
- If there is an existing agent inbox/action panel, follow-ups can live there as a subsection.

## UX Behavior

For a gap:

1. User clicks “Ask follow-up.”
2. Show a small focused input with suggested prompts.
3. Submit creates a follow-up with `opportunity_id`.
4. The new follow-up appears as queued/pending.

For a theme:

1. User clicks “Ask follow-up.”
2. Submit creates a follow-up with `cluster_id`.

For market-level questions:

1. User can ask from Activity or agent panel.
2. Submit creates a follow-up without opportunity/cluster id.

## Suggested Prompt Chips

Use concise prompt chips such as:

- “Why is this credible?”
- “What evidence is strongest?”
- “Which users feel this most?”
- “What would invalidate this?”
- “Find more like this”
- “Ignore this pattern”

Chips should fill the input but allow editing before submit.

## Follow-Up List

Show follow-ups grouped by status:

- Queued
- Answered
- Dismissed

Queued:

- Show question text.
- Show “Agent will answer after next run” or current pending state.
- Allow dismiss.

Answered:

- Show question and response.
- Include linked gap/theme context when available.

Dismissed:

- Keep collapsed or low prominence.

## Copy Guidelines

Use user-facing words:

- Question
- Answer
- Agent
- Gap
- Theme

Avoid user-facing words:

- follow_up_id
- opportunity_id
- cluster_id
- metadata

## Safety and Clarity

- Do not imply answers are instant unless the backend actually returns an answer.
- If the answer is generated later, show queued state clearly.
- If the answer references evidence, link back to the gap/theme/finding where possible.
- If a follow-up cannot be answered, show a concise failure state and let the user dismiss it.

## Acceptance Criteria

- Users can ask a follow-up from a gap context.
- Users can view queued and answered follow-ups for the selected market.
- Users can dismiss follow-ups.
- The UI uses the new answer/dismiss endpoints.
- The flow does not look like a general chat app.
- The primary Gaps page remains focused; follow-up UI is secondary and contextual.

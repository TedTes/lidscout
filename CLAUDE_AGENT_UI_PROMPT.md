# Claude Code Prompt: Agent-Oriented Niche UI

You are improving the LidScout web client UI/UX. Focus on product flow, hierarchy, and interaction behavior. Keep the existing visual system unless a layout change is needed. Do not redesign the brand or styling.

## Goal

Make the app feel like a continuous AI research agent for product managers and solo founders.

The user-facing model should be:

1. The user defines a niche scope.
2. The agent monitors configured companies and sources on a schedule.
3. The agent surfaces ranked gaps backed by evidence.
4. The user gives feedback that changes future runs.

Use `niche` in user-facing copy. Avoid `market` in visible UI text, even though API fields still use `market_id`.

## Backend Endpoints Available

Use these existing endpoints:

- `GET /markets/{market_id}/agent/activity`
- `GET /markets/{market_id}/agent/memory`
- `GET /markets/{market_id}/agent/preferences`
- `PUT /markets/{market_id}/agent/preferences`
- `GET /markets/{market_id}/agent/feedback`
- `POST /opportunities/{opportunity_id}/feedback`

Do not invent new backend endpoints. If a desired interaction needs backend support that does not exist, leave the control out or mark it as a non-functional placeholder only if the current app already uses that pattern.

## Agent Activity Feed

Add a secondary activity surface for the selected niche. It should not replace the gaps list.

Use `GET /markets/{market_id}/agent/activity`.

Activity event types:

- `run_started`
- `run_completed`
- `source_failed`
- `feedback_recorded`
- `preferences_updated`

The feed should help the user understand what the agent recently did:

- started a run
- completed a run and found/fetched/extracted/synthesized counts
- hit source failures
- recorded feedback
- updated research preferences

Keep this concise. Prefer short rows or a compact side panel/drawer/section over a large dashboard block.

## Agent Memory Summary

Add a compact "what the agent remembers" surface for the selected niche.

Use `GET /markets/{market_id}/agent/memory`.

Display:

- `headline`
- `learned_preferences`
- `source_notes`
- `feedback_notes`

This should read like a research agent memory snapshot, not a settings page. Keep it close to the niche scope or agent state area.

## Feedback Loop

On gap cards, make feedback feel like training the agent.

Use `POST /opportunities/{opportunity_id}/feedback` with:

- `save`
- `dismiss`
- `more_like_this`
- `less_like_this`

Use short labels or icon buttons. Avoid long explanatory text. After feedback, refresh or update:

- the gap card state
- the activity feed
- the memory summary if visible

Do not make feedback the dominant visual element. It should be easy but secondary to reading the gap.

## Research Preferences

If there is already a niche settings or scope editing surface, include agent preferences there.

Use:

- `GET /markets/{market_id}/agent/preferences`
- `PUT /markets/{market_id}/agent/preferences`

Fields:

- `preferred_source_families`
- `ignored_themes`
- `ignored_categories`
- `muted_source_ids`
- `extra_instructions`

Frame this as refining what the agent should pay attention to. Do not expose raw implementation terms more than necessary.

## Navigation And Layout

Keep the current niche-first structure:

- left side: user’s niches
- selected niche: gaps-first view
- secondary chips/actions for themes, findings, reports, sources

Do not reintroduce top-level Gaps/Themes/Findings/Reports/Sources nav.

The agent surfaces should be secondary:

- activity feed
- memory summary
- preferences/scope refinement

Do not make a manual pipeline trigger a primary action.

## Copy Rules

Use:

- niche
- agent
- gaps
- themes
- findings
- sources
- evidence

Avoid visible copy using:

- market
- signal
- cluster
- competitor as a primary page label

Companies can appear as metadata inside evidence, sources, and breadth indicators.

## Acceptance Criteria

- Selected niche view clearly feels like an agent is monitoring and reporting back.
- Activity feed uses `/agent/activity` and handles empty state.
- Memory summary uses `/agent/memory` and handles empty state.
- Gap feedback supports save, dismiss, more-like-this, less-like-this.
- Feedback refreshes relevant client state without a full page reload where practical.
- Existing API client types are updated cleanly.
- No backend changes.
- No styling overhaul.

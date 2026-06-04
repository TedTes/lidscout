# Claude Code Prompt: Source Quality UI

You are improving the LidScout web client Sources tab. Focus on making source quality actionable for the user. Keep the existing dark visual system and layout density; do not do a visual redesign.

## Goal

The Sources tab should help a user answer:

1. Which sources are currently useful?
2. Which sources are blocked or noisy?
3. What should I fix, replace, pause, or leave alone?

Monitored sources must remain the primary content. Suggested/replacement sources should not dominate the page.

## New API Fields

Each source can now include:

- `quality_status`: `productive | noisy | blocked | untested | stale`
- `quality_reason`: short explanation
- `replacement_suggestions`: optional list of alternatives for blocked/noisy/stale sources
  - `trigger`: `blocked_source | low_yield | stale_source | missing_family`
  - `reason`: explanation for why the replacement is suggested
  - `replaces_source_id`: source being replaced
  - `candidate`: same shape as `SourceSuggestion`
- `health`: optional stats object
  - `total_runs`
  - `success_count`
  - `failure_count`
  - `consecutive_failures`
  - `posts_fetched_count`
  - `relevant_posts_count`
  - `extracted_signals_count`
  - `opportunity_count`
  - `last_status`
  - `last_error`
  - `last_fetched_count`
  - `last_relevant_count`
  - `last_extracted_count`
  - `last_opportunity_count`
  - `fetch_success_rate`
  - `relevance_yield_rate`
  - `signal_yield_rate`
  - `last_scanned_at`
  - `updated_at`

Use these fields instead of recalculating quality ad hoc in the component.

## Source Row Behavior

Each monitored source row should show:

- URL/domain
- Scope tag: company name or niche-wide
- Source family/type
- Enabled/paused state
- Quality badge from `quality_status`
- Short `quality_reason`
- Last scanned time or "Not scanned yet"
- Last error if present

Quality badge guidance:

- `productive`: green, label "Productive"
- `noisy`: amber, label "Noisy"
- `blocked`: red/rose, label "Blocked"
- `untested`: slate/blue, label "Untested"
- `stale`: amber/slate, label "Stale"

Do not overuse bright colors. The badge should help scanning, not dominate the row.

## Stats Display

If `health` exists, show compact useful stats only:

- `{relevant_posts_count} relevant`
- `{extracted_signals_count} findings`
- `{opportunity_count} opportunities`
- optionally `{fetch_success_rate * 100}% fetch success`

Do not show every raw counter by default.

If the source is noisy, surface why:

- Example: "45 posts scanned, 0 relevant"

If blocked:

- Prefer the real error or quality reason.
- Keep it concise.

## Actions

Keep current actions:

- Enable / pause
- Remove
- Add source via plus button

Add no new destructive action unless the backend already supports it.

Replacement suggestions are now available on each source as `replacement_suggestions`.
Make them secondary:

- Small "Suggested alternatives" expander inside or directly below the affected source row
- Only show when a source is `blocked`, `noisy`, or `stale`
- Do not put suggestions above monitored sources
- Do not show replacement suggestions for productive or untested sources
- Each alternative should show:
  - candidate label
  - source family/type
  - concise rationale
  - why it is suggested
  - URL/domain
- Avoid making alternatives feel auto-applied. They are recommendations until the user adds one.

Suggested copy examples:

- Blocked source: `This source is blocked. Try a gate-free alternative.`
- Noisy source: `This source has low yield. Try a higher-signal source.`
- Stale source: `This source has not produced fresh data recently.`

## Empty States

If no sources exist:

- Tell the user to add a monitored source.
- Avoid talking about templates or internals.

If all sources are untested:

- Say sources will be scored after the first scan.

## Acceptance Criteria

- Monitored sources are still the first and main section.
- Each row shows `quality_status` and `quality_reason`.
- Blocked/noisy/stale sources are easy to spot.
- Productive sources are visually distinct but not flashy.
- Replacement suggestions appear only for blocked/noisy/stale sources and remain secondary.
- No raw `signal` or `cluster` wording is introduced.
- Existing source add/remove/pause behavior keeps working.

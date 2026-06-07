# Claude Code Prompt: Evidence Provenance UI

You are improving the LidScout web client UI/UX. Focus on trust, evidence provenance, and reducing source-management prominence. Keep the existing visual system and do not restyle unrelated surfaces.

## Goal

Make sources visible where they matter: inside opportunity cards, theme provenance, and evidence drilldowns. Do not make users manage sources as a primary workflow.

The user should be able to answer:

- Why should I trust this opportunity?
- Which quote/source supports it?
- Is this based on one noisy post or multiple source families?
- Which source families are producing the theme?

## Backend Data Now Available

The API response has additive provenance fields.

`GET /opportunities?market_id=...` opportunity items include:

- `evidence_items[]`
  - `id`
  - `signal_id`
  - `post_id`
  - `quote`
  - `pain`
  - `url`
  - `source_label`
  - `source_family`
  - `source_type`
  - `company_id`
  - `company_name`
  - `category`
  - `urgency`
  - `severity`
  - `confidence`
  - `detected_at`
- `source_family_breakdown[]`
  - `source_family`
  - `count`

`GET /clusters?market_id=...` theme items include:

- `source_family_breakdown[]`
  - `source_family`
  - `count`

`GET /signals?market_id=...` signal items include:

- `source_label`
- `source_family`
- `source_type`

Update TypeScript types in `web_client/lib/types/signals.ts` before rendering these fields.

## Navigation

Demote `Sources` from primary navigation.

Preferred primary nav:

- Opportunities
- Evidence
- Activity

If removing `Sources` completely is risky, move it behind a secondary affordance:

- `Activity -> Coverage details`
- or a small power-user expandable labelled `Research coverage`

Do not keep `Sources` as a top-level tab with equal weight to Opportunities.

## Opportunity Cards

Each opportunity card should surface evidence provenance inline.

Required card elements:

- Existing title, pain, affected user, possible wedge.
- Evidence trail line:
  - Example: `Evidence trail: 3 quotes · 2 sources`
- Compact source family/source labels:
  - Example: `GitHub · Hacker News`
  - or `Technical forums 2 · Social 1`
- A `View evidence` action.

When `View evidence` is clicked, show an evidence drawer/expandable panel with:

- Verbatim quote from `evidence_items[].quote`
- Source label/family/type
- Company name when present
- Clickable original URL
- Date/time when present
- Pain/category/severity metadata when useful

Do not expose raw IDs to the user.

## Themes / Evidence View

If the current app has a separate Themes page, it can either remain or be folded into Evidence. In either case, theme cards must show provenance:

- Source family breakdown from `source_family_breakdown`
  - Example: `Technical forums 6 · Social 2 · Reviews 1`
- Company/source diversity if already available.
- Top examples remain useful, but provenance should be visible before long summaries.

## Evidence View

The Evidence view should behave as the place to inspect raw findings/signals.

Each evidence item should show:

- Quote / evidence text
- Source label and source family
- Company name if present
- Original URL
- Category, urgency/severity

Use `Evidence`, not `Signals`, in user-facing navigation.

## Source Management

Do not make custom source addition prominent.

If source controls remain:

- Put them in `Activity -> Coverage details` or a collapsed advanced section.
- Show monitored sources first.
- Show failing/blocked/paused health clearly.
- Custom source addition should feel like “Suggest a source for the agent to evaluate,” not “manually configure crawler.”

Remove or demote any large “Suggested sources” container unless it directly supports coverage diagnostics.

## Empty / Running States

When no opportunities exist but a scan is running:

- Center the scan progress in the empty content area.
- Keep source/provenance language concrete:
  - `Scanning 5 sources`
  - `Reviewing posts`
  - `Extracting evidence`
  - `Identifying opportunities`

When no opportunities exist and no scan is running:

- Explain that the agent has not found enough evidence yet.
- Offer one action:
  - `Run scan`
  - or `Improve coverage`

## Acceptance Criteria

- Opportunity cards show evidence trail and source attribution without opening the Sources tab.
- `View evidence` reveals quote-level attribution with clickable URLs.
- Themes show source-family breakdown.
- `Sources` is no longer a primary tab, or is clearly demoted behind coverage/settings.
- TypeScript types match the new backend fields.
- No raw source-management workflow is promoted as a core user action.
- Existing visual style remains consistent.

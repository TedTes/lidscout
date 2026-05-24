# Claude Code Prompt: Market-First UI Reframe

You are improving the LidScout web client UI/UX. Focus on product flow and information hierarchy, not visual restyling. Keep the existing visual system unless a layout change is required by the new behavior.

## Goal

Reframe the app from company-first monitoring to market-first gap intelligence.

The user should experience the product as:

1. Pick a market/niche.
2. See ranked gaps for that market.
3. Inspect themes and findings behind each gap.
4. Manage sources monitored for that market.

Companies are still important, but they should appear as context and evidence metadata, not as primary navigation.

## Vocabulary

Use these user-facing terms:

- Market: watched niche/category.
- Gap: synthesized product opportunity.
- Theme: grouped complaint/pain pattern.
- Finding: individual extracted evidence signal.
- Source: monitored URL/feed/API source.
- Company: monitored company inside a market.

Avoid user-facing terms:

- Signal
- Cluster
- Competitor as primary page/nav label

Internal code can keep existing names where changing them would be risky.

## Navigation

Update the app shell so the active market is the workspace context.

Recommended navigation hierarchy:

- Active market selector in the top/header area.
- Main pages:
  - Gaps
  - Themes
  - Findings
  - Reports
  - Sources

Do not add a top-level Companies page. Companies should be managed inside a market context.

Remove or hide any visible pipeline trigger from primary navigation. Pipeline runs should feel like background automation, not a user-facing core workflow.

## Data Scoping

All dashboard pages should pass the active `market_id` to API calls when available:

- `GET /signals?market_id=...`
- `GET /clusters?market_id=...`
- `GET /opportunities?market_id=...`
- `GET /reports/latest?market_id=...`
- `GET /sources?market_id=...`

Use `GET /markets` to populate the active market selector.

If no market exists, show a focused empty state to create/select a market. Do not show global mixed data as the default state.

## Gaps Page

This is the primary landing page after dashboard entry.

Show gap cards using `/opportunities?market_id=...`.

Each card should emphasize:

- Gap title
- Suggested wedge
- Target user
- Evidence count
- Company breadth:
  - `company_count`
  - `market_company_count`
  - Example display: `Appears across 3 of 7 companies`
- Company names as compact metadata

Do not make raw numeric confidence the dominant signal. If shown, keep it secondary.

## Themes Page

Use `/clusters?market_id=...`.

Each theme should show:

- Theme name
- Summary
- Frequency / findings count
- Average score
- Company breadth:
  - `company_count`
  - `market_company_count`
  - `company_names`
- Top examples

Theme cards should link to related findings when possible.

## Findings Page

Use `/signals?market_id=...`.

Each finding must show:

- Pain / evidence summary
- Company name (`competitor_name`)
- Market name if helpful (`market_name`)
- Evidence URL
- Evidence text excerpt
- Category
- Urgency/severity

The company appears here as context, not navigation.

## Sources Page

Reframe from "company management" to:

`Sources monitored for {market name}`

Use `/sources?market_id=...`.

The source list response now includes an optional `summary` object:

- `source_count`
- `active_count`
- `disabled_count`
- `error_count`
- `company_count`
- `by_family[]` with `source_family`, `source_count`, `active_count`, `error_count`, `company_count`

Use this summary for the page stat row and source-family grouping counts instead of recalculating everything ad hoc in the component.

Show a flat list grouped by source family/type:

- Reviews
- Social
- Technical forums
- Owned content
- Other

Each row should include:

- Source label or URL
- Company tag (`competitor_name`) if company-scoped
- Market tag (`market_name`) if market-scoped
- Source family (`source_family`)
- Enabled/disabled
- Last scanned time
- Last error

The UI may still allow adding a source for a company, but that interaction should live under the active market context.

## Source Suggestions

Market-first suggestions:

- Use `GET /markets/{market_id}/source-suggestions`

Company-level suggestions are secondary:

- Use `GET /competitors/{competitor_id}/source-suggestions`

If company suggestions are shown, present them under a market setup or source setup flow, not as global navigation.

## Company Setup

Companies are managed inside a market context.

Use:

- `GET /markets/{market_id}/competitors`
- `POST /markets/{market_id}/competitors`

Avoid using global `POST /competitors` from the UI when the user is inside an active market. The global route can remain as a backend/admin escape hatch.

## Reports Page

Use `/reports/latest?market_id=...`.

Report title/subtitle should reflect the active market context.

Show:

- Top gaps/opportunities
- Top themes
- Emerging pains
- Evidence/company breadth where available

## Empty States

Empty states should guide setup in this order:

1. Create/select market.
2. Add/confirm companies inside the market.
3. Add/confirm sources for the market.
4. Wait for background scan / run pipeline only from admin context.

Do not present a manual pipeline run as the main action.

## Acceptance Criteria

- Dashboard no longer defaults to unscoped global data when markets exist.
- Primary page is Gaps or market-level overview, not raw findings.
- Company/competitor is not a top-level navigation item.
- Gaps and themes visibly show company breadth.
- Findings visibly show company/source evidence context.
- Sources are scoped to active market and show company tags.
- Pipeline trigger is removed from primary navigation.
- Existing API client types are updated or reused correctly.
- No styling overhaul unless needed to support the revised hierarchy.

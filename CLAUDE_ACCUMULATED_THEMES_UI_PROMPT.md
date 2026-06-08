# Claude Code Prompt: Use Accumulated Themes In The Themes Tab

You are improving the LidScout web client after the backend added durable accumulated themes.

## Goal

Move the product-facing Themes tab off the legacy cluster endpoint and onto the accumulated theme model.

The Themes tab should show durable unmet-need patterns accumulated across scans, not per-run clusters.

## Backend Contract

Use:

- `GET /themes?market_id={marketId}`

The response shape is:

```ts
{
  themes: Array<{
    id: string
    theme: string
    summary: string
    status: 'emerging' | 'qualified' | 'rejected' | 'archived'
    qualification_status: 'qualified' | 'not_promoted'
    qualification_rejection_reason: string | null
    signal_ids: string[] // legacy-compatible finding ids
    finding_ids: string[]
    frequency: number
    average_score: number
    top_examples: string[]
    company_ids: string[]
    company_names: string[]
    company_count: number
    market_company_count: number | null
    evidence_source_count: number
    source_family_breakdown: Array<{ source_family: string; count: number }>
    evidence_items: Array<{
      id: string
      signal_id: string | null
      post_id: string | null
      quote: string | null
      pain: string | null
      url: string | null
      source_label: string | null
      source_family: string | null
      source_type: string | null
      company_id: string | null
      company_name: string | null
      category: string | null
      urgency: 'low' | 'medium' | 'high' | null
      severity: 'low' | 'medium' | 'high' | null
      confidence: number | null
      detected_at: string | null
    }>
    latest_finding_at: string | null
    last_qualified_at: string | null
  }>
}
```

## UI Behavior

- Keep the visible tab label as `Evidence` if that is the current navigation direction, but the content can still be theme cards/pattern cards.
- Replace `/clusters?market_id=...` calls in the Themes/Evidence tab with `/themes?market_id=...`.
- Do not add back global stat cards or extra filters.
- Emphasize:
  - theme title,
  - summary,
  - evidence count,
  - source count,
  - company breadth,
  - source-family breakdown,
  - top evidence quotes with source labels and links.
- If a theme has `status: qualified`, visually indicate it as opportunity-ready, but keep that indicator secondary.
- If there are no themes yet:
  - show a compact empty state explaining that evidence patterns appear after the agent reviews enough relevant posts,
  - do not show a large diagnostic panel.

## Important Constraints

- Do not reintroduce the Sources tab as primary navigation.
- Do not show noisy agent internals like filtered/evaluating posts in the main evidence view.
- Keep the current visual system and spacing direction.
- Preserve mobile layout quality. The tab row and account/avatar area should remain stable across tabs.
- Avoid changing backend code in this task.

## Acceptance Criteria

- Themes/Evidence page no longer depends on `GET /clusters` for its primary content.
- Theme cards show source attribution and evidence quotes from `evidence_items`.
- Theme cards show source-family breakdown from `source_family_breakdown`.
- Empty state is concise and user-facing.
- Existing Opportunities tab still works with theme-backed opportunities.

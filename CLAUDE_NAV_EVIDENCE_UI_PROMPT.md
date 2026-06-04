# Claude Code Prompt: Simplify Workspace Navigation

You are improving the LidScout web client UI/UX. Focus on navigation structure and information hierarchy, not visual restyling. Keep the existing dark visual system unless a layout change is required.

## Goal

Simplify the selected niche workspace around the user's actual workflow:

1. Review synthesized opportunities.
2. Verify the evidence behind them.
3. Manage monitored sources.
4. Understand what the agent did.

Use this top-level tab structure:

- Opportunities
- Evidence
- Sources
- Activity

Do not keep `Themes`, `Findings`, and `Reports` as equal top-level tabs.

## Vocabulary

Use these user-facing words:

- Niche or market, whichever the current UI already uses consistently
- Opportunity
- Evidence
- Pattern
- Finding
- Quote
- Source
- Agent activity

Avoid user-facing words:

- Signal
- Cluster
- Raw signal
- Agent metadata

Internal code names can stay as-is if changing them would be risky.

## Navigation Changes

Replace the current tab row:

`Opportunities | Themes | Findings | Sources | Reports | Agent Activity`

With:

`Opportunities | Evidence | Sources | Activity`

Rules:

- `Opportunities` remains the primary default tab.
- `Evidence` combines what currently lives under Themes and Findings.
- `Activity` replaces `Agent Activity` in the tab label.
- `Reports` should be demoted out of the main tabs for now.

## Evidence Tab

The Evidence tab should help users verify why opportunities exist.

It should include two internal sections or segmented controls:

- Patterns
- Findings

Patterns:

- Backed by `/clusters?market_id=...`
- User-facing label: `Patterns`
- Show recurring pain themes, frequency, company breadth if available, and top examples.
- Avoid using `cluster` in visible text.

Findings:

- Backed by `/signals?market_id=...`
- User-facing label: `Findings`
- Show individual extracted evidence items with source URL, company/source context, category, and excerpt.
- Use `Finding` or `Quote` depending on the existing component content. Prefer `Finding` if the item is summarized, `Quote` if it is mostly raw text.

The Evidence tab should not feel like a dumping ground. It should answer:

> "What proof is behind the opportunities?"

## Opportunities Tab

Keep Opportunities as the main product surface.

Each opportunity should continue to emphasize:

- Title
- Observed pain
- Affected user
- Possible wedge
- Evidence trail
- Verification note
- Save / dismiss controls

If possible, the Evidence Trail should link into the Evidence tab filtered to the relevant pattern/findings.

## Reports

Do not keep Reports as a top-level tab.

Demote it to one of these secondary surfaces:

- A small `Latest report` link/button inside Activity.
- An export/share action if report data exists.
- A secondary item inside a menu.

If reports are not currently useful, hide the entry rather than preserving a weak tab.

## Sources Tab

Keep Sources as a top-level tab.

Sources should remain operational:

- Monitored sources first.
- Ability to add/remove sources.
- Source health/status visible.
- Suggested sources should not dominate the page.

## Activity Tab

Rename `Agent Activity` to `Activity`.

Activity should show real operational events, not theatrical sub-agent labels.

Prefer events such as:

- Last scan completed
- Sources scanned
- Posts reviewed
- Findings extracted
- Opportunities synthesized
- Actions proposed/executed
- Next scan time

Avoid fake role rows like:

- Research Scout waiting
- Signal Analyst waiting
- Gap Synthesizer waiting

## Routing

Keep existing routes if a route rename would be risky, but update labels and navigation behavior.

Acceptable implementation:

- `/markets/[marketId]/themes` can redirect to `/markets/[marketId]/evidence?view=patterns`
- `/markets/[marketId]/findings` can redirect to `/markets/[marketId]/evidence?view=findings`
- Or keep old routes internally but render the new Evidence UI.

Do not break deep links unnecessarily.

## Responsive Behavior

The four tabs should fit cleanly on mobile:

`Opportunities | Evidence | Sources | Activity`

If spacing is tight:

- Use horizontal scrolling tabs.
- Keep tab position consistent across pages.
- Do not let avatar/account controls collide with tabs.

## Acceptance Criteria

- Main workspace tabs are `Opportunities`, `Evidence`, `Sources`, `Activity`.
- `Themes` and `Findings` are no longer top-level tabs.
- Evidence tab contains both Patterns and Findings views.
- `Reports` is no longer a primary tab.
- Existing APIs are reused where possible.
- No raw `signal` or `cluster` language is shown to users.
- Mobile tab layout remains stable and uncluttered.
- Primary Opportunities page remains the default workspace view.

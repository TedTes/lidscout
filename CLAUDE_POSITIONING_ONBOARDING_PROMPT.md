# Claude Code Prompt: Agent Positioning And Onboarding Copy

You are improving LidScout UI copy and onboarding clarity. Do not restyle the product. Keep the current layout and visual system unless a copy change creates a clear spacing issue.

## Goal

Make the product consistently explain itself as:

> An AI research agent that monitors public market signals and surfaces product opportunities.

The app should feel like a delegated research agent, not a generic analytics dashboard.

## Copy Rules

- Prefer "AI research agent" over "dashboard", "signal intelligence", or "market intelligence platform".
- Prefer "opportunities" for synthesized gaps.
- Prefer "evidence" for raw supporting posts/findings.
- Use "market" in setup actions like "Add market".
- Keep "niche" only where it already helps explain the sidebar/workspace mental model.
- Avoid promising fully autonomous behavior the product does not yet support.

## Areas To Review

- Marketing hero and CTA copy.
- Auth/login supporting copy.
- Add-market modal/drawer copy.
- First-run empty states.
- Agent running/scanning empty state.
- Sources tab empty state and source explanation text.
- Activity tab labels where agent work is shown.

## Acceptance Criteria

- A new user can understand within 10 seconds:
  - what the agent monitors,
  - why sources were chosen,
  - when results should appear,
  - what to do if no opportunities appear.
- The product does not read like a generic report dashboard.
- Copy changes use shared constants from `web_client/lib/positioning.ts` where practical.
- No broad visual redesign.

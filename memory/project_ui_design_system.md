---
name: project-ui-design-system
description: LidScout web dashboard design system — dark intelligence theme, sidebar layout, color tokens, component library
metadata:
  type: project
---

LidScout uses a dark "intelligence dashboard" design language across the web_client Next.js app.

**Why:** Redesigned from a basic gray/white prototype to a premium dark UI suited for a market intelligence tool.

**How to apply:** All new UI components and pages should follow this system.

## Layout
- Fixed left sidebar (`w-[220px]`) on `lg:` breakpoints via `DashboardNav`
- Main content has `lg:ml-[220px]` to clear the sidebar
- Mobile: sticky top bar with compact nav
- `DashboardShell` wraps every page and includes the nav

## Color tokens (Tailwind classes)
- Page background: `bg-[#07091a]`
- Card/surface: `bg-slate-900/40` with `border-slate-800/80`
- Elevated: `bg-slate-800/30` with `border-slate-800/60`
- Primary text: `text-slate-100` / `text-slate-200`
- Secondary text: `text-slate-400` / `text-slate-500`
- Muted: `text-slate-600`
- Brand/accent: `violet-600` (buttons), `violet-400` (text/icons), `violet-600/[0.13]` (active nav bg)
- High urgency: `rose-500` bar, `rose-400` text, `rose-500/10` bg, `rose-500/20` border
- Medium urgency: `amber-500` bar, `amber-400` text
- Low urgency: `slate-700` bar, `slate-500` text
- Success/WTP: `emerald-400` text, `emerald-500/10` bg

## Component library (`DashboardPrimitives.tsx`)
- `Metric` — stat card, accepts `accent` boolean for violet variant
- `ScoreBadge` — colored score pill (green ≥8, amber ≥6, gray <6)
- `UrgencyBadge` — colored dot + label for high/medium/low
- `Chip` — gray category/meta tag
- `ClusterLink` — violet link with chevron arrow
- `SectionCard` — dark card wrapper with optional title
- `EmptyPanel`, `ErrorPanel`, `LoadingPanel` — state placeholders
- `Divider` — `h-px bg-slate-800/80`

## Signal urgency left bar pattern
Signal rows use a narrow `w-1` colored div inside `flex overflow-hidden rounded-xl`:
```tsx
<div className="flex overflow-hidden rounded-xl border border-slate-800/70">
  <div className={`w-1 shrink-0 ${urgencyBarColor}`} />
  <div className="flex-1 px-4 py-3.5">...</div>
</div>
```

## Scrollbar + selection
Custom dark scrollbar and violet text selection defined in `globals.css`.

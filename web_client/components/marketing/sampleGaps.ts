export type SampleGap = {
  id: string;
  market: string;
  company: string;
  title: string;
  painSummary: string;
  evidenceQuote: string;
  sourceLabel: string;
  sourceUrl: string;
  mentions: number;
  strength: 'strong' | 'moderate';
  suggestedWedge: string;
};

export const sampleGaps: SampleGap[] = [
  {
    id: '1',
    market: 'Workspace tools',
    company: 'Notion',
    title: 'Calendar reliability blocks team adoption',
    painSummary:
      'Shared calendars fail to sync reliably across timezones, causing teams to abandon the feature and revert to dedicated calendar tools.',
    evidenceQuote:
      'We tried to move our whole team to Notion Calendar but the timezone sync issues made it unusable after two weeks. Back to Google Calendar.',
    sourceLabel: 'r/Notion',
    sourceUrl: 'https://reddit.com/r/Notion',
    mentions: 14,
    strength: 'strong',
    suggestedWedge:
      'A lightweight timezone-aware event sync layer that treats Notion as the source of truth while resolving conflicts server-side.',
  },
  {
    id: '2',
    market: 'Workspace tools',
    company: 'Notion',
    title: 'Database views degrade past 1,000 rows',
    painSummary:
      'Filtered gallery and board views become sluggish or unresponsive as databases grow, forcing users to split data across multiple databases.',
    evidenceQuote:
      'Performance becomes completely unacceptable above 1,000 rows. We had to move our CRM data out — a database tool that can\'t handle data is a hard sell.',
    sourceLabel: 'G2 Reviews',
    sourceUrl: 'https://g2.com/products/notion',
    mentions: 11,
    strength: 'strong',
    suggestedWedge:
      'Virtualised table rendering with server-side filtering that keeps the UI responsive regardless of database size.',
  },
  {
    id: '3',
    market: 'Workspace tools',
    company: 'Notion',
    title: 'API rate limits prevent reliable integrations',
    painSummary:
      'The 3 req/s rate limit makes real-time sync workflows infeasible, pushing developers toward fragile polling workarounds or abandoning integrations entirely.',
    evidenceQuote:
      'The rate limits make it impossible to build anything that needs real-time sync. I\'ve had to explain to stakeholders why "it\'s an API limitation" three times this month.',
    sourceLabel: 'Hacker News',
    sourceUrl: 'https://news.ycombinator.com',
    mentions: 9,
    strength: 'moderate',
    suggestedWedge:
      'Webhook-first integration model with burst allowances for initial sync, eliminating the need for polling entirely.',
  },
  {
    id: '4',
    market: 'Product operations',
    company: 'Linear',
    title: 'Roadmap views lack executive-friendly export',
    painSummary:
      'Engineering teams can\'t share roadmap progress without taking screenshots or rebuilding the view in a presentation tool, adding friction to every stakeholder update.',
    evidenceQuote:
      'I love Linear internally but every sprint review I have to recreate our roadmap in slides. A PDF export or shareable link that non-Linear users can read would save me an hour a week.',
    sourceLabel: 'r/ProjectManagement',
    sourceUrl: 'https://reddit.com/r/ProjectManagement',
    mentions: 9,
    strength: 'moderate',
    suggestedWedge:
      'Read-only shareable roadmap views with PDF export — no Linear account required to view.',
  },
  {
    id: '5',
    market: 'Design collaboration',
    company: 'Figma',
    title: 'Simultaneous edits cause silent data loss',
    painSummary:
      'Multiple editors working on complex component libraries create merge conflicts that resolve incorrectly and silently, discovered only when designs are already in development.',
    evidenceQuote:
      'Lost three hours of component work because someone else was editing the same library. Figma showed no conflict — we only noticed when the dev handed back the build.',
    sourceLabel: 'Figma Community',
    sourceUrl: 'https://forum.figma.com',
    mentions: 7,
    strength: 'moderate',
    suggestedWedge:
      'Per-component locking with visible co-presence indicators that surface conflicts before they overwrite work.',
  },
  {
    id: '6',
    market: 'Project management',
    company: 'Asana',
    title: 'Workload ignores calendar time, makes capacity meaningless',
    painSummary:
      'Workload view counts tasks without accounting for meeting-heavy weeks, rendering capacity planning unreliable and leading to consistent underestimation of delivery dates.',
    evidenceQuote:
      'Workload looks fine on paper but doesn\'t know that this person is in 6 hours of meetings on Tuesday. We\'ve learned to ignore it and just ask people directly.',
    sourceLabel: 'G2 Reviews',
    sourceUrl: 'https://g2.com/products/asana',
    mentions: 6,
    strength: 'moderate',
    suggestedWedge:
      'Calendar integration that reduces available capacity in Workload based on scheduled meeting time, making the view reflect reality.',
  },
];

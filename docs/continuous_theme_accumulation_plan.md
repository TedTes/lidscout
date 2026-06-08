# Continuous Theme Accumulation Plan

## Direction

Build the next pipeline around durable accumulated findings and themes rather than per-run clusters.

The current product has no active users, so this work can use a clean product-facing model without preserving old generated cluster data. Keep `posts`, `niche_sources`, `user_niches`, and `agent_activity`; add the accumulated model beside the legacy `signals/clusters/opportunities` path, then migrate the worker to the new path.

## Production Storage Choice

Use pgvector as the production embedding store.

The migration should enable the `vector` extension and store finding embeddings and theme centroids as vector columns. JSON embedding storage is acceptable only inside test doubles or local development fallback code. It should not be the production path because Python-side similarity across accumulated findings/themes will become slow quickly.

## Product Tables

Add:

- `findings`: durable extracted evidence from relevant posts.
- `themes`: durable unmet-need clusters for one user niche.
- `theme_findings`: membership/provenance link between themes and findings.

Later, opportunities should be synthesized from qualified themes. The existing `opportunities` table can be extended to reference a source theme before replacing the old cluster-based contract.

## Assignment Rules

Each new finding should be embedded and compared against existing theme centroids for the same user niche.

- Similarity `>= 0.82`: assign automatically.
- Similarity `0.70` to `< 0.82`: ask the LLM whether the finding describes the same unmet need as the candidate theme.
- Similarity `< 0.70`: do not assign.

For borderline matches, evaluate the best matching themes in order, capped at three candidates. If the LLM says yes, assign and update the theme. If all candidates are rejected, create a new theme.

This prevents clustering by broad topic or vendor name when the underlying unmet needs are different.

## Theme Updates

When a finding is assigned to a theme:

- append a `theme_findings` row,
- update finding/source/company counts,
- update latest evidence timestamp,
- update the centroid from member embeddings,
- mark the theme as changed in the current run.

Only changed themes should be requalified and resynthesized.

## Opportunity Qualification

Qualification must use accumulated theme evidence, not just the current run.

A theme should become an opportunity only when it passes these gates:

- minimum evidence count, normally at least two findings,
- source diversity, normally at least two sources,
- buyer or user context is present,
- pain intensity is non-trivial through urgency, severity, workaround, switching, or willingness-to-pay evidence,
- the pattern is on-niche for the user's research brief,
- the gap is not only a vendor bug/fix request unless it generalizes across tools or workflows,
- the suggested wedge implies a new product or workflow opportunity, not merely "vendor should fix this."

High-signal sources can justify a narrower exception, but that exception must be explicit in the qualification reason and visible in activity/debug metadata.

## Rollout Order

1. Add pgvector-backed accumulated schema.
2. Add domain models and repository contracts.
3. Add PostgreSQL repository implementation.
4. Add theme assignment service with high-confidence and borderline LLM paths.
5. Persist extracted findings and embeddings from the worker.
6. Assign only newly inserted findings to themes.
7. Requalify changed themes.
8. Synthesize/update opportunities from qualified themes.
9. Point API/UI reads to accumulated opportunities/evidence.
10. Retire or demote legacy per-run `clusters` once the new path is stable.

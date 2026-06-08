# Continuous Theme Accumulation Audit

## Current Control Flow

The scheduled agent path is:

1. Celery Beat enqueues `workers.tasks.run_daily_pipeline_all`.
2. `run_daily_pipeline_all` loads active `user_niches` and enqueues `workers.tasks.run_pipeline_for_market` for each niche with enabled sources.
3. `run_pipeline_for_market` builds `PipelineConfig` in `workers/jobs.py`.
4. `workers/run_daily_pipeline.py` runs the pipeline for that one user niche.

Manual API-triggered scans use the same worker task path when the API enqueues `run_pipeline_for_market`.

## Current Source Input Model

The pipeline is already source-configurable. `_configured_sources()` resolves the active `user_niche` to its adopted template, loads enabled `niche_sources`, applies source preferences and source health gates, and maps each row into a `SourceInput`.

The source quality layer already affects selection:

- `source_scan_eligibility()` blocks or delays unhealthy sources.
- `source_observed_quality_score()` helps prioritize higher-yield sources.
- proxy/auth gated sources are skipped unless the run explicitly allows them.

This means the right source control point is `niche_sources`, not hard-coded worker source lists.

## Current Persistence Behavior

The pipeline persists several artifacts:

- `posts`: raw fetched posts, deduped by `(source, source_id)`.
- `signals`: extracted findings from posts.
- `scores`: scores for extracted signals.
- `clusters`: current-run signal clusters.
- `opportunities`: current-run opportunities synthesized from current-run clusters.
- `agent_activity`: user-visible and diagnostic run events.
- source health/relevance stats on `niche_sources`.

Raw posts are persisted across runs, but downstream processing is not accumulated.

## Current Run Isolation

Each run fetches posts, persists them, then continues processing the in-memory `posts` list returned by that fetch. Relevance filtering, extraction, scoring, embedding, clustering, and opportunity synthesis are all based on the current run's fetched posts/signals.

Existing historical posts and signals are not loaded back into clustering or synthesis. Previously extracted signals therefore do not strengthen future clusters unless they are fetched and processed again in the current run.

## Current Clustering Behavior

`ClusteringService` clusters only the signals passed into the method. It groups by company first, then uses cosine similarity against in-memory bucket centroids. Clusters are saved with deterministic per-run ids like `cluster-1`, `cluster-2`.

That works for one batch, but it is not a durable theme memory:

- cluster ids are not stable across runs,
- cluster centroids are not persisted,
- theme membership is not persisted as a first-class relationship,
- accumulated evidence is not considered during synthesis.

## Current Opportunity Qualification

Opportunity qualification is stricter than earlier versions. It requires evidence count, source diversity, source quality, buyer context, pain intensity, cross-tool patterns, and on-niche checks before promotion.

The limitation is scope, not only logic: the qualification sees only current-run cluster signals. A theme with one useful finding today and one useful finding tomorrow cannot qualify from accumulated evidence because the pipeline does not link findings into persistent themes.

## Main Gap

The missing architecture is a rolling finding-to-theme memory:

1. Persist each extracted finding as reusable evidence.
2. Embed the finding and compare it to existing theme centroids for the same user niche.
3. Assign the finding to an existing theme or create a new theme.
4. Update theme counts, source/company breadth, latest evidence, and centroid.
5. Requalify only themes changed by the current run.
6. Synthesize or update opportunities from qualified accumulated themes.

This should be built around product-facing concepts:

- `findings`: extracted evidence/pain signals.
- `themes`: durable accumulated unmet-need clusters.
- `theme_findings`: assignment/provenance link.
- `opportunities`: promoted qualified themes.

The legacy `signals/clusters/opportunities` path can remain during migration, but it should no longer be the long-term source of product value.

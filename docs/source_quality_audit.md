# Source Quality Audit

This audit captures the source-quality state that already exists before adding
more adaptive source recommendations.

## Stored source metadata

`niche_sources` stores mostly static or operator-controlled quality hints:

- `enabled`
- `health_status`: `unknown`, `active`, `failing`, `paused`
- `last_scanned_at`
- `last_error`
- `tier`
- `signal_quality_score`
- `is_gate_free`
- `buyer_voice_verified`
- `access_mode`
- `requires_proxy`
- `requires_auth`
- `recommended_cadence`

These fields describe whether a source should be scanned and its expected or
observed value.

## Stored run health

`niche_source_health_stats` stores cumulative and last-run performance:

- run reliability: `total_runs`, `success_count`, `failure_count`,
  `consecutive_failures`, `last_status`, `last_error`
- fetch volume: `posts_fetched_count`, `last_fetched_count`
- relevance yield: `relevant_posts_count`, `last_relevant_count`,
  `rule_filtered_count`, `llm_filtered_count`, `relevance_failed_count`
- extraction yield: `extracted_signals_count`, `last_extracted_count`
- opportunity yield: `gap_count`, `last_gap_count`
- rejection reasons: `rejection_breakdown`, `last_rejection_breakdown`
- recency: `last_scanned_at`, `updated_at`

The worker updates these stats after runs and uses them to update
`signal_quality_score`.

## Existing scoring

`application.source_quality.source_observed_quality_score` already computes an
observed score from:

- reliability
- relevance rate
- extraction rate
- opportunity/gap rate
- consecutive failure penalty

Unknown sources default to `0.5`.

## Current API gap

`api.routes.signals._serialize_niche_source` currently returns:

```json
"health": null
```

for niche sources, even though the repository can load
`NicheSourceRunStats`. The frontend therefore sees lifecycle labels and
`signal_quality_score`, but not the detailed stats or user-friendly source
quality status.

## Next implementation target

Expose a derived source quality status in source API responses:

- `productive`
- `noisy`
- `blocked`
- `untested`
- `stale`

The status should be derived from the existing source metadata plus
`NicheSourceRunStats`, without adding new database columns for the MVP.

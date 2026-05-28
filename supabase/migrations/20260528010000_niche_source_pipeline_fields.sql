-- Add pipeline runtime fields to niche_sources and create niche_source_health.
--
-- niche_sources gains the same operational fields that monitored_sources had so
-- the pipeline can treat them identically: enabled flag, limit, scan frequency,
-- last error, and the options blob the adapter layer reads.

alter table niche_sources
    add column if not exists enabled       boolean  not null default true,
    add column if not exists limit_value   integer,
    add column if not exists scan_frequency text,
    add column if not exists last_error    text,
    add column if not exists options       jsonb    not null default '{}'::jsonb;

alter table niche_sources
    add constraint niche_sources_limit_positive
        check (limit_value is null or limit_value >= 1);

create index if not exists niche_sources_niche_enabled_idx
    on niche_sources (niche_id, enabled);

-- Cumulative health counters per niche_source — mirrors the old source_health
-- table but keyed to niche_source_id instead of monitored_source_id.
create table if not exists niche_source_health (
    niche_source_id          uuid primary key references niche_sources(id) on delete cascade,
    total_runs               integer not null default 0,
    success_count            integer not null default 0,
    failure_count            integer not null default 0,
    consecutive_failures     integer not null default 0,
    posts_fetched_count      integer not null default 0,
    relevant_posts_count     integer not null default 0,
    extracted_signals_count  integer not null default 0,
    gap_count                integer not null default 0,
    last_status              text    not null default 'unknown',
    last_error               text,
    last_fetched_count       integer not null default 0,
    last_relevant_count      integer not null default 0,
    last_extracted_count     integer not null default 0,
    last_gap_count           integer not null default 0,
    last_scanned_at          timestamptz,
    updated_at               timestamptz,
    constraint niche_source_health_last_status_check
        check (last_status in ('unknown', 'healthy', 'failing')),
    constraint niche_source_health_counts_non_negative check (
        total_runs >= 0
        and success_count >= 0
        and failure_count >= 0
        and consecutive_failures >= 0
        and posts_fetched_count >= 0
        and relevant_posts_count >= 0
        and extracted_signals_count >= 0
        and gap_count >= 0
        and last_fetched_count >= 0
        and last_relevant_count >= 0
        and last_extracted_count >= 0
        and last_gap_count >= 0
    )
);

create index if not exists niche_source_health_status_idx
    on niche_source_health (last_status);

create index if not exists niche_source_health_updated_at_idx
    on niche_source_health (updated_at desc);

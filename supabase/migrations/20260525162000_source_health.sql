create table if not exists source_health (
    monitored_source_id text primary key references monitored_sources(id) on delete cascade,
    total_runs integer not null default 0,
    success_count integer not null default 0,
    failure_count integer not null default 0,
    consecutive_failures integer not null default 0,
    posts_fetched_count integer not null default 0,
    relevant_posts_count integer not null default 0,
    extracted_signals_count integer not null default 0,
    opportunity_count integer not null default 0,
    last_status text not null default 'unknown',
    last_error text,
    last_fetched_count integer not null default 0,
    last_relevant_count integer not null default 0,
    last_extracted_count integer not null default 0,
    last_opportunity_count integer not null default 0,
    last_scanned_at timestamptz,
    updated_at timestamptz,
    constraint source_health_last_status_check
        check (last_status in ('unknown', 'healthy', 'failing')),
    constraint source_health_counts_non_negative check (
        total_runs >= 0
        and success_count >= 0
        and failure_count >= 0
        and consecutive_failures >= 0
        and posts_fetched_count >= 0
        and relevant_posts_count >= 0
        and extracted_signals_count >= 0
        and opportunity_count >= 0
        and last_fetched_count >= 0
        and last_relevant_count >= 0
        and last_extracted_count >= 0
        and last_opportunity_count >= 0
    )
);

create index if not exists source_health_status_idx
    on source_health(last_status);

create index if not exists source_health_updated_at_idx
    on source_health(updated_at desc);

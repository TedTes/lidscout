-- Track scan health and cumulative yield for catalog-backed sources per user
-- niche. This replaces the need to write catalog source stats into the legacy
-- niche_source_health_stats table, which is keyed to niche_sources rows.

create table if not exists user_source_run_stats (
    user_niche_id               uuid        not null references user_niches(id) on delete cascade,
    source_id                   uuid        not null references sources(id) on delete cascade,
    template_source_binding_id  uuid        references template_sources(id) on delete set null,
    total_runs                  integer     not null default 0,
    success_count               integer     not null default 0,
    failure_count               integer     not null default 0,
    consecutive_failures        integer     not null default 0,
    posts_fetched_count         integer     not null default 0,
    relevant_posts_count        integer     not null default 0,
    rule_filtered_count         integer     not null default 0,
    llm_filtered_count          integer     not null default 0,
    relevance_failed_count      integer     not null default 0,
    extracted_signals_count     integer     not null default 0,
    gap_count                   integer     not null default 0,
    last_status                 text        not null default 'unknown',
    last_error                  text,
    last_fetched_count          integer     not null default 0,
    last_relevant_count         integer     not null default 0,
    last_rule_filtered_count    integer     not null default 0,
    last_llm_filtered_count     integer     not null default 0,
    last_relevance_failed_count integer     not null default 0,
    last_extracted_count        integer     not null default 0,
    last_gap_count              integer     not null default 0,
    rejection_breakdown         jsonb       not null default '{}'::jsonb,
    last_rejection_breakdown    jsonb       not null default '{}'::jsonb,
    last_scanned_at             timestamptz,
    updated_at                  timestamptz not null default now(),
    primary key (user_niche_id, source_id),
    constraint user_source_run_stats_last_status_check
        check (last_status in ('unknown', 'healthy', 'failing')),
    constraint user_source_run_stats_non_negative_counts check (
        total_runs >= 0
        and success_count >= 0
        and failure_count >= 0
        and consecutive_failures >= 0
        and posts_fetched_count >= 0
        and relevant_posts_count >= 0
        and rule_filtered_count >= 0
        and llm_filtered_count >= 0
        and relevance_failed_count >= 0
        and extracted_signals_count >= 0
        and gap_count >= 0
        and last_fetched_count >= 0
        and last_relevant_count >= 0
        and last_rule_filtered_count >= 0
        and last_llm_filtered_count >= 0
        and last_relevance_failed_count >= 0
        and last_extracted_count >= 0
        and last_gap_count >= 0
    ),
    constraint user_source_run_stats_rejection_breakdown_object
        check (jsonb_typeof(rejection_breakdown) = 'object'),
    constraint user_source_run_stats_last_rejection_breakdown_object
        check (jsonb_typeof(last_rejection_breakdown) = 'object')
);

create index if not exists user_source_run_stats_source_id_idx
    on user_source_run_stats (source_id);

create index if not exists user_source_run_stats_binding_id_idx
    on user_source_run_stats (template_source_binding_id);

create index if not exists user_source_run_stats_scanned_idx
    on user_source_run_stats (user_niche_id, last_scanned_at desc);

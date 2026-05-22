create table if not exists pipeline_run_metrics (
    id text primary key,
    ran_at timestamptz not null default now(),
    fetched_count integer not null default 0,
    fetch_failed_count integer not null default 0,
    rule_filtered_count integer not null default 0,
    llm_filtered_count integer not null default 0,
    relevance_failed_count integer not null default 0,
    extraction_attempted_count integer not null default 0,
    extracted_count integer not null default 0,
    no_signal_count integer not null default 0,
    extraction_failed_count integer not null default 0,
    signal_inserted_count integer not null default 0,
    scored_count integer not null default 0,
    scoring_failed_count integer not null default 0,
    average_score double precision not null default 0,
    embedding_failed_count integer not null default 0,
    clustered_count integer not null default 0,
    cluster_inserted_count integer not null default 0,
    opportunity_synthesized_count integer not null default 0,
    opportunity_inserted_count integer not null default 0,
    opportunity_failed_count integer not null default 0,
    email_sent boolean not null default false,
    email_error text
);

create index if not exists idx_pipeline_run_metrics_ran_at
    on pipeline_run_metrics (ran_at desc);

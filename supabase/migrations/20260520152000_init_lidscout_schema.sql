create table if not exists posts (
    id text primary key,
    source text not null,
    source_id text not null,
    title text not null default '',
    body text not null default '',
    author text,
    url text,
    created_at timestamptz,
    upvotes integer,
    comments_count integer,
    metadata jsonb not null default '{}'::jsonb,
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint posts_source_not_empty check (btrim(source) <> ''),
    constraint posts_source_id_not_empty check (btrim(source_id) <> ''),
    constraint posts_unique_source_record unique (source, source_id)
);

create index if not exists posts_source_created_at_idx
    on posts (source, created_at desc);

create table if not exists signals (
    id text primary key,
    post_id text not null references posts(id) on delete cascade,
    pain text not null,
    user_type text,
    job_to_be_done text,
    current_workaround text,
    urgency text not null,
    severity text not null,
    willingness_to_pay boolean,
    category text,
    confidence numeric not null,
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint signals_pain_not_empty check (btrim(pain) <> ''),
    constraint signals_urgency_value check (urgency in ('low', 'medium', 'high')),
    constraint signals_severity_value check (severity in ('low', 'medium', 'high')),
    constraint signals_confidence_range check (confidence >= 0 and confidence <= 1)
);

create index if not exists signals_post_id_idx
    on signals (post_id);

create index if not exists signals_category_idx
    on signals (category);

create table if not exists scores (
    signal_id text primary key references signals(id) on delete cascade,
    total_score numeric not null,
    urgency_score numeric not null,
    severity_score numeric not null,
    willingness_score numeric not null,
    confidence_score numeric not null,
    reasoning text not null,
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint scores_total_score_range check (total_score >= 0 and total_score <= 10),
    constraint scores_component_scores_non_negative check (
        urgency_score >= 0
        and severity_score >= 0
        and willingness_score >= 0
        and confidence_score >= 0
    )
);

create table if not exists clusters (
    id text primary key,
    theme text not null,
    summary text not null,
    signal_ids text[] not null default array[]::text[],
    frequency integer not null,
    average_score numeric not null,
    top_examples text[] not null default array[]::text[],
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint clusters_theme_not_empty check (btrim(theme) <> ''),
    constraint clusters_frequency_non_negative check (frequency >= 0),
    constraint clusters_average_score_range check (
        average_score >= 0 and average_score <= 10
    )
);

create index if not exists clusters_average_score_idx
    on clusters (average_score desc);

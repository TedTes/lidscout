create type niche_status as enum ('defined', 'sourced', 'active');

create table if not exists niches (
    id                   uuid          primary key default gen_random_uuid(),
    job                  text          not null,
    buyer                text          not null,
    category             text          not null,
    description          text,
    status               niche_status  not null default 'defined',
    monitorability_score float,
    -- opportunity_score is intentionally null at definition time.
    -- It is computed from synthesized gaps after monitoring produces findings.
    -- Never assign a value at seed time.
    opportunity_score    float,
    created_at           timestamptz   not null default now(),
    updated_at           timestamptz   not null default now(),
    constraint niches_job_not_empty   check (btrim(job)   <> ''),
    constraint niches_buyer_not_empty check (btrim(buyer) <> '')
);

create unique index if not exists niches_job_unique_idx on niches (lower(btrim(job)));
create index if not exists niches_category_idx on niches (category);
create index if not exists niches_status_idx   on niches (status);

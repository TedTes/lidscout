create table if not exists competitors (
    id text primary key,
    name text not null,
    website text,
    category text,
    description text,
    created_at timestamptz not null default now(),
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint competitors_name_not_empty check (btrim(name) <> '')
);

create index if not exists competitors_category_idx
    on competitors (category);

create table if not exists monitored_sources (
    id text primary key,
    competitor_id text not null references competitors(id) on delete cascade,
    locator text not null unique,
    source_type text not null,
    enabled boolean not null default true,
    limit_value integer,
    scan_frequency text,
    last_scanned_at timestamptz,
    last_error text,
    options jsonb not null default '{}'::jsonb,
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint monitored_sources_locator_not_empty check (btrim(locator) <> ''),
    constraint monitored_sources_source_type_not_empty check (btrim(source_type) <> ''),
    constraint monitored_sources_limit_positive check (
        limit_value is null or limit_value >= 1
    )
);

create index if not exists monitored_sources_competitor_enabled_idx
    on monitored_sources (competitor_id, enabled);

create table if not exists signal_evidence (
    signal_id text primary key,
    competitor_id text references competitors(id) on delete set null,
    evidence_url text,
    evidence_text text,
    detected_at timestamptz not null default now(),
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists signal_evidence_competitor_detected_at_idx
    on signal_evidence (competitor_id, detected_at desc);

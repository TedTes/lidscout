create table if not exists opportunities (
    id text primary key,
    cluster_id text not null references clusters(id) on delete cascade,
    title text not null,
    target_user text not null,
    pain_summary text not null,
    why_it_matters text not null,
    suggested_wedge text not null,
    evidence_count integer not null check (evidence_count > 0),
    confidence double precision not null check (confidence >= 0 and confidence <= 1),
    evidence_signal_ids jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_opportunities_cluster_id
    on opportunities(cluster_id);

create index if not exists idx_opportunities_confidence
    on opportunities(confidence desc);

create table if not exists agent_alerts (
    id text primary key,
    market_id text not null references markets(id) on delete cascade,
    alert_type text not null,
    title text not null,
    severity text not null default 'info',
    status text not null default 'open',
    detail text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    acknowledged_at timestamptz,
    constraint agent_alerts_severity_check
        check (severity in ('info', 'warning', 'critical')),
    constraint agent_alerts_status_check
        check (status in ('open', 'acknowledged'))
);

create index if not exists agent_alerts_market_created_at_idx
    on agent_alerts(market_id, created_at desc);

create index if not exists agent_alerts_market_status_idx
    on agent_alerts(market_id, status);

create table if not exists agent_follow_ups (
    id text primary key,
    market_id text not null references markets(id) on delete cascade,
    question text not null,
    opportunity_id text references opportunities(id) on delete set null,
    cluster_id text references clusters(id) on delete set null,
    status text not null default 'queued',
    response text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint agent_follow_ups_status_check
        check (status in ('queued', 'answered', 'dismissed'))
);

create index if not exists agent_follow_ups_market_created_at_idx
    on agent_follow_ups(market_id, created_at desc);

create index if not exists agent_follow_ups_market_status_idx
    on agent_follow_ups(market_id, status);

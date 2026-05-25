create table if not exists agent_activity (
    id text primary key,
    market_id text not null references markets(id) on delete cascade,
    event_type text not null,
    title text not null,
    detail text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    constraint agent_activity_event_type_check
        check (
            event_type in (
                'run_started',
                'run_completed',
                'source_failed',
                'feedback_recorded',
                'preferences_updated'
            )
        )
);

create index if not exists agent_activity_market_created_at_idx
    on agent_activity(market_id, created_at desc);

create index if not exists agent_activity_market_event_type_idx
    on agent_activity(market_id, event_type);

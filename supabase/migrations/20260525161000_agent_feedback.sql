create table if not exists agent_feedback (
    id text primary key,
    market_id text not null references markets(id) on delete cascade,
    opportunity_id text not null references opportunities(id) on delete cascade,
    action text not null,
    reason text,
    created_at timestamptz not null default now(),
    constraint agent_feedback_action_check
        check (action in ('save', 'dismiss', 'more_like_this', 'less_like_this'))
);

create index if not exists agent_feedback_market_created_at_idx
    on agent_feedback(market_id, created_at desc);

create index if not exists agent_feedback_opportunity_idx
    on agent_feedback(opportunity_id);

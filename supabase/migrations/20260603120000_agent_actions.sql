create table if not exists agent_actions (
    id text primary key,
    user_niche_id uuid not null references user_niches(id) on delete cascade,
    action_type text not null,
    status text not null default 'proposed',
    reason text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    completed_at timestamptz,
    constraint agent_actions_action_type_check
        check (
            action_type in (
                'scan_sources',
                'pause_source',
                'suggest_source',
                'answer_follow_up',
                'send_alert',
                'wait'
            )
        ),
    constraint agent_actions_status_check
        check (
            status in (
                'proposed',
                'approved',
                'dismissed',
                'completed',
                'failed'
            )
        )
);

create index if not exists agent_actions_user_niche_created_at_idx
    on agent_actions (user_niche_id, created_at desc);

create index if not exists agent_actions_user_niche_status_idx
    on agent_actions (user_niche_id, status);

create index if not exists agent_actions_user_niche_action_type_idx
    on agent_actions (user_niche_id, action_type);

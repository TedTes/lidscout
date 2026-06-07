alter table if exists agent_actions
    drop constraint if exists agent_actions_action_type_check;

alter table if exists agent_actions
    add constraint agent_actions_action_type_check
        check (
            action_type in (
                'scan_sources',
                'pause_source',
                'source_needs_attention',
                'suggest_source',
                'answer_follow_up',
                'send_alert',
                'wait'
            )
        );

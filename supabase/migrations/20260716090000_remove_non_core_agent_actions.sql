drop table if exists agent_actions;
drop table if exists agent_alerts;
drop table if exists agent_follow_ups;

delete from agent_activity
where event_type in (
    'alert_created',
    'follow_up_recorded',
    'follow_up_answered',
    'follow_up_dismissed',
    'actions_proposed',
    'actions_executed'
);

alter table if exists agent_activity
    drop constraint if exists agent_activity_event_type_check;

alter table if exists agent_activity
    add constraint agent_activity_event_type_check
        check (
            event_type in (
                'run_started',
                'run_completed',
                'sources_scanned',
                'posts_filtered',
                'signals_extracted',
                'clusters_formed',
                'gaps_synthesized',
                'source_failed',
                'feedback_recorded',
                'preferences_updated',
                'brief_updated',
                'post_evaluating',
                'post_accepted',
                'post_filtered',
                'theme_promoted',
                'theme_rejected'
            )
        );

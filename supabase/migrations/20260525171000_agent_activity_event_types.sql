alter table if exists agent_activity
    drop constraint if exists agent_activity_event_type_check;

alter table if exists agent_activity
    add constraint agent_activity_event_type_check
        check (
            event_type in (
                'run_started',
                'run_completed',
                'source_failed',
                'feedback_recorded',
                'preferences_updated',
                'brief_updated',
                'alert_created',
                'follow_up_recorded'
            )
        );

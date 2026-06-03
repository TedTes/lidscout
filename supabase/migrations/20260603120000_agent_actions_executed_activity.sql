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
                'alert_created',
                'follow_up_recorded',
                'post_evaluating',
                'post_accepted',
                'post_filtered',
                'theme_promoted',
                'theme_rejected',
                'actions_proposed',
                'actions_executed'
            )
        );

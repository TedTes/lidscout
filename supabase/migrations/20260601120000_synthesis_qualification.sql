alter table if exists opportunities
    add column if not exists unmet_need_type text;

alter table if exists opportunities
    drop constraint if exists opportunities_unmet_need_type_check;

alter table if exists opportunities
    add constraint opportunities_unmet_need_type_check
        check (
            unmet_need_type is null
            or unmet_need_type in ('time', 'money', 'effort', 'capability', 'fit')
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
                'alert_created',
                'follow_up_recorded',
                'post_evaluating',
                'post_accepted',
                'post_filtered',
                'theme_promoted',
                'theme_rejected'
            )
        );

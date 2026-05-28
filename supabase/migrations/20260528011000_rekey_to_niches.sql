-- Rekey agent state tables from market_id to user_niche_id, and rekey
-- signal_evidence from competitor_id/market_id to niche_company_id/niche_id.
--
-- Old market-scoped rows are cleared first — they belong to the old data model
-- and are not forward-compatible with user_niches (different ID type: text vs uuid).

-- ── signal_evidence ───────────────────────────────────────────────────────────

alter table signal_evidence
    drop column if exists competitor_id,
    drop column if exists market_id;

alter table signal_evidence
    add column if not exists niche_id         uuid references niches(id)         on delete set null,
    add column if not exists niche_company_id uuid references niche_companies(id) on delete set null;

drop index if exists signal_evidence_competitor_detected_at_idx;
drop index if exists signal_evidence_market_detected_at_idx;

create index if not exists signal_evidence_niche_detected_at_idx
    on signal_evidence (niche_id, detected_at desc);

create index if not exists signal_evidence_niche_company_detected_at_idx
    on signal_evidence (niche_company_id, detected_at desc);

-- ── agent_preferences ─────────────────────────────────────────────────────────

truncate table agent_preferences;

alter table agent_preferences
    drop constraint if exists agent_preferences_pkey,
    drop constraint if exists agent_preferences_market_id_fkey,
    drop column if exists market_id;

alter table agent_preferences
    add column if not exists user_niche_id uuid references user_niches(id) on delete cascade;

update agent_preferences set user_niche_id = gen_random_uuid() where user_niche_id is null;

alter table agent_preferences
    alter column user_niche_id set not null,
    add primary key (user_niche_id);

-- ── agent_feedback ────────────────────────────────────────────────────────────

truncate table agent_feedback;

alter table agent_feedback
    drop constraint if exists agent_feedback_market_id_fkey,
    drop column if exists market_id;

alter table agent_feedback
    add column if not exists user_niche_id uuid not null references user_niches(id) on delete cascade
        default gen_random_uuid();

alter table agent_feedback alter column user_niche_id drop default;

drop index if exists agent_feedback_market_created_at_idx;
create index if not exists agent_feedback_user_niche_created_at_idx
    on agent_feedback (user_niche_id, created_at desc);

-- ── agent_activity ────────────────────────────────────────────────────────────

truncate table agent_activity;

alter table agent_activity
    drop constraint if exists agent_activity_market_id_fkey,
    drop column if exists market_id;

alter table agent_activity
    add column if not exists user_niche_id uuid not null references user_niches(id) on delete cascade
        default gen_random_uuid();

alter table agent_activity alter column user_niche_id drop default;

drop index if exists agent_activity_market_created_at_idx;
drop index if exists agent_activity_market_event_type_idx;
create index if not exists agent_activity_user_niche_created_at_idx
    on agent_activity (user_niche_id, created_at desc);
create index if not exists agent_activity_user_niche_event_type_idx
    on agent_activity (user_niche_id, event_type);

-- ── agent_alerts ──────────────────────────────────────────────────────────────

truncate table agent_alerts;

alter table agent_alerts
    drop constraint if exists agent_alerts_market_id_fkey,
    drop column if exists market_id;

alter table agent_alerts
    add column if not exists user_niche_id uuid not null references user_niches(id) on delete cascade
        default gen_random_uuid();

alter table agent_alerts alter column user_niche_id drop default;

drop index if exists agent_alerts_market_created_at_idx;
drop index if exists agent_alerts_market_status_idx;
create index if not exists agent_alerts_user_niche_created_at_idx
    on agent_alerts (user_niche_id, created_at desc);
create index if not exists agent_alerts_user_niche_status_idx
    on agent_alerts (user_niche_id, status);

-- ── agent_follow_ups ──────────────────────────────────────────────────────────

truncate table agent_follow_ups;

alter table agent_follow_ups
    drop constraint if exists agent_follow_ups_market_id_fkey,
    drop column if exists market_id;

alter table agent_follow_ups
    add column if not exists user_niche_id uuid not null references user_niches(id) on delete cascade
        default gen_random_uuid();

alter table agent_follow_ups alter column user_niche_id drop default;

drop index if exists agent_follow_ups_market_created_at_idx;
drop index if exists agent_follow_ups_market_status_idx;
create index if not exists agent_follow_ups_user_niche_created_at_idx
    on agent_follow_ups (user_niche_id, created_at desc);
create index if not exists agent_follow_ups_user_niche_status_idx
    on agent_follow_ups (user_niche_id, status);

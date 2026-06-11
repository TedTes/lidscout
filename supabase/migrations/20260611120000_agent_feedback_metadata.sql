alter table agent_feedback
    add column if not exists comment text,
    add column if not exists updated_at timestamptz;

update agent_feedback
set updated_at = coalesce(updated_at, created_at, now())
where updated_at is null;

alter table agent_feedback
    alter column updated_at set not null,
    alter column updated_at set default now();

delete from agent_feedback a
using agent_feedback b
where a.user_niche_id = b.user_niche_id
  and a.opportunity_id = b.opportunity_id
  and a.action = b.action
  and (
      coalesce(a.updated_at, a.created_at) < coalesce(b.updated_at, b.created_at)
      or (
          coalesce(a.updated_at, a.created_at) = coalesce(b.updated_at, b.created_at)
          and a.id < b.id
      )
  );

delete from agent_feedback a
using agent_feedback b
where a.user_niche_id = b.user_niche_id
  and a.opportunity_id = b.opportunity_id
  and a.action in ('save', 'dismiss')
  and b.action in ('save', 'dismiss')
  and a.action <> b.action
  and (
      coalesce(a.updated_at, a.created_at) < coalesce(b.updated_at, b.created_at)
      or (
          coalesce(a.updated_at, a.created_at) = coalesce(b.updated_at, b.created_at)
          and a.id < b.id
      )
  );

delete from agent_feedback a
using agent_feedback b
where a.user_niche_id = b.user_niche_id
  and a.opportunity_id = b.opportunity_id
  and a.action in ('more_like_this', 'less_like_this')
  and b.action in ('more_like_this', 'less_like_this')
  and a.action <> b.action
  and (
      coalesce(a.updated_at, a.created_at) < coalesce(b.updated_at, b.created_at)
      or (
          coalesce(a.updated_at, a.created_at) = coalesce(b.updated_at, b.created_at)
          and a.id < b.id
      )
  );

create unique index if not exists agent_feedback_scope_action_idx
    on agent_feedback (user_niche_id, opportunity_id, action);

create index if not exists agent_feedback_user_niche_opportunity_idx
    on agent_feedback (user_niche_id, opportunity_id);

-- Normalize user-level source ownership.
--
-- Final source model:
--   sources          = canonical locator/type/access metadata
--   template_sources = default source set for a template niche
--   user_sources     = concrete source binding and overrides for one user niche
--
-- user_source_preferences remains temporarily as a compatibility table while
-- the application code is moved to user_sources.

create table if not exists user_sources (
    id                         uuid        primary key default gen_random_uuid(),
    user_niche_id              uuid        not null references user_niches(id) on delete cascade,
    source_id                  uuid        not null references sources(id) on delete cascade,
    template_source_binding_id uuid        references template_sources(id) on delete set null,
    enabled                    boolean     not null default true,
    muted                      boolean     not null default false,
    cadence                    text,
    priority                   integer,
    limit_value                integer,
    options                    jsonb       not null default '{}'::jsonb,
    created_at                 timestamptz not null default now(),
    updated_at                 timestamptz not null default now(),
    constraint user_sources_limit_positive
        check (limit_value is null or limit_value >= 1),
    constraint user_sources_priority_positive
        check (priority is null or priority >= 1),
    constraint user_sources_options_object
        check (jsonb_typeof(options) = 'object')
);

create unique index if not exists user_sources_user_source_idx
    on user_sources (user_niche_id, source_id);

create index if not exists user_sources_source_id_idx
    on user_sources (source_id);

create index if not exists user_sources_template_binding_idx
    on user_sources (template_source_binding_id);

create index if not exists user_sources_enabled_idx
    on user_sources (user_niche_id, enabled, muted);

-- Materialize template defaults for every adopted user niche. This gives every
-- source that the resolver can display a concrete row that user actions and
-- worker stats can reference.
insert into user_sources (
    user_niche_id,
    source_id,
    template_source_binding_id,
    enabled,
    muted,
    cadence,
    priority,
    limit_value,
    options,
    created_at,
    updated_at
)
select
    un.id,
    ts.source_id,
    ts.id,
    ts.default_enabled,
    false,
    ts.default_scan_frequency,
    ts.tier,
    ts.default_limit_value,
    ts.default_options,
    greatest(un.created_at, ts.created_at),
    now()
from user_niches un
join template_sources ts
  on ts.template_niche_id = un.template_niche_id
on conflict (user_niche_id, source_id) do update
set template_source_binding_id = coalesce(
        user_sources.template_source_binding_id,
        excluded.template_source_binding_id
    ),
    updated_at = now();

-- Preserve existing per-user overrides created during the first catalog pass.
insert into user_sources (
    id,
    user_niche_id,
    source_id,
    template_source_binding_id,
    enabled,
    muted,
    cadence,
    priority,
    limit_value,
    options,
    created_at,
    updated_at
)
select
    usp.id,
    usp.user_niche_id,
    usp.source_id,
    ts.id,
    coalesce(usp.enabled, ts.default_enabled, true),
    usp.muted,
    coalesce(usp.cadence_override, ts.default_scan_frequency),
    coalesce(usp.priority_override, ts.tier),
    coalesce(usp.limit_override, ts.default_limit_value),
    case
        when usp.options_override = '{}'::jsonb then coalesce(ts.default_options, '{}'::jsonb)
        else usp.options_override
    end,
    usp.created_at,
    usp.updated_at
from user_source_preferences usp
left join user_niches un
  on un.id = usp.user_niche_id
left join template_sources ts
  on ts.template_niche_id = un.template_niche_id
 and ts.source_id = usp.source_id
on conflict (user_niche_id, source_id) do update
set enabled = excluded.enabled,
    muted = excluded.muted,
    cadence = excluded.cadence,
    priority = excluded.priority,
    limit_value = excluded.limit_value,
    options = excluded.options,
    updated_at = excluded.updated_at;

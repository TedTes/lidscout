-- Introduce canonical sources, template-source defaults, and per-user source
-- preferences. niche_sources remains as the compatibility table until API and
-- worker reads are fully moved to the new model.

create table if not exists sources (
    id              uuid        primary key default gen_random_uuid(),
    locator         text        not null,
    source_type     text        not null,
    source_family   text        not null,
    is_gate_free    boolean     not null default false,
    access_mode     text        not null default 'unknown',
    requires_proxy  boolean     not null default false,
    requires_auth   boolean     not null default false,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    constraint sources_locator_not_empty check (btrim(locator) <> ''),
    constraint sources_type_not_empty check (btrim(source_type) <> ''),
    constraint sources_family_not_empty check (btrim(source_family) <> '')
);

create unique index if not exists sources_type_locator_idx
    on sources (source_type, locator);

create index if not exists sources_family_idx
    on sources (source_family);

create index if not exists sources_access_mode_idx
    on sources (access_mode);

create table if not exists template_sources (
    id                              uuid        primary key default gen_random_uuid(),
    template_niche_id               uuid        not null references niches(id) on delete cascade,
    source_id                       uuid        not null references sources(id) on delete cascade,
    company_id                      uuid        references niche_companies(id) on delete set null,
    default_enabled                 boolean     not null default true,
    default_limit_value             integer,
    default_scan_frequency          text,
    default_buyer_voice_verified    boolean     not null default false,
    default_options                 jsonb       not null default '{}'::jsonb,
    tier                            integer,
    signal_quality_score            numeric,
    recommended_cadence             text,
    created_at                      timestamptz not null default now(),
    updated_at                      timestamptz not null default now(),
    constraint template_sources_limit_positive
        check (default_limit_value is null or default_limit_value >= 1),
    constraint template_sources_tier_range
        check (tier is null or tier between 1 and 5),
    constraint template_sources_signal_quality_range
        check (
            signal_quality_score is null
            or (signal_quality_score >= 0 and signal_quality_score <= 1)
        ),
    constraint template_sources_options_object
        check (jsonb_typeof(default_options) = 'object')
);

create unique index if not exists template_sources_template_source_idx
    on template_sources (template_niche_id, source_id);

create index if not exists template_sources_template_enabled_idx
    on template_sources (template_niche_id, default_enabled);

create index if not exists template_sources_source_id_idx
    on template_sources (source_id);

create table if not exists user_source_preferences (
    id                 uuid        primary key default gen_random_uuid(),
    user_niche_id      uuid        not null references user_niches(id) on delete cascade,
    source_id          uuid        not null references sources(id) on delete cascade,
    enabled            boolean,
    muted              boolean     not null default false,
    cadence_override   text,
    priority_override  integer,
    limit_override     integer,
    options_override   jsonb       not null default '{}'::jsonb,
    created_at         timestamptz not null default now(),
    updated_at         timestamptz not null default now(),
    constraint user_source_preferences_limit_positive
        check (limit_override is null or limit_override >= 1),
    constraint user_source_preferences_priority_positive
        check (priority_override is null or priority_override >= 1),
    constraint user_source_preferences_options_object
        check (jsonb_typeof(options_override) = 'object')
);

create unique index if not exists user_source_preferences_user_source_idx
    on user_source_preferences (user_niche_id, source_id);

create index if not exists user_source_preferences_source_id_idx
    on user_source_preferences (source_id);

create index if not exists user_source_preferences_muted_idx
    on user_source_preferences (user_niche_id, muted);

insert into sources (
    locator,
    source_type,
    source_family,
    is_gate_free,
    access_mode,
    requires_proxy,
    requires_auth,
    created_at,
    updated_at
)
select
    ns.locator,
    ns.source_type,
    (array_agg(ns.source_family order by ns.updated_at desc, ns.created_at desc))[1],
    bool_or(ns.is_gate_free),
    (array_agg(ns.access_mode order by ns.updated_at desc, ns.created_at desc))[1],
    bool_or(ns.requires_proxy),
    bool_or(ns.requires_auth),
    min(ns.created_at),
    max(ns.updated_at)
from niche_sources ns
group by ns.source_type, ns.locator
on conflict (source_type, locator) do update
set source_family = excluded.source_family,
    is_gate_free = sources.is_gate_free or excluded.is_gate_free,
    access_mode = excluded.access_mode,
    requires_proxy = sources.requires_proxy or excluded.requires_proxy,
    requires_auth = sources.requires_auth or excluded.requires_auth,
    updated_at = greatest(sources.updated_at, excluded.updated_at);

insert into template_sources (
    template_niche_id,
    source_id,
    company_id,
    default_enabled,
    default_limit_value,
    default_scan_frequency,
    default_buyer_voice_verified,
    default_options,
    tier,
    signal_quality_score,
    recommended_cadence,
    created_at,
    updated_at
)
select
    ns.niche_id,
    s.id,
    ns.company_id,
    ns.enabled,
    ns.limit_value,
    ns.scan_frequency,
    ns.buyer_voice_verified,
    ns.options,
    ns.tier,
    ns.signal_quality_score,
    ns.recommended_cadence,
    ns.created_at,
    ns.updated_at
from niche_sources ns
join sources s
  on s.source_type = ns.source_type
 and s.locator = ns.locator
on conflict (template_niche_id, source_id) do update
set company_id = coalesce(excluded.company_id, template_sources.company_id),
    default_enabled = excluded.default_enabled,
    default_limit_value = excluded.default_limit_value,
    default_scan_frequency = excluded.default_scan_frequency,
    default_buyer_voice_verified = excluded.default_buyer_voice_verified,
    default_options = excluded.default_options,
    tier = excluded.tier,
    signal_quality_score = excluded.signal_quality_score,
    recommended_cadence = excluded.recommended_cadence,
    updated_at = greatest(template_sources.updated_at, excluded.updated_at);

insert into user_source_preferences (
    user_niche_id,
    source_id,
    muted,
    created_at,
    updated_at
)
select distinct
    ap.user_niche_id,
    s.id,
    true,
    now(),
    now()
from agent_preferences ap
cross join lateral jsonb_array_elements_text(ap.muted_source_ids) muted(source_ref)
join niche_sources ns
  on ns.id::text = muted.source_ref
join sources s
  on s.source_type = ns.source_type
 and s.locator = ns.locator
where jsonb_typeof(ap.muted_source_ids) = 'array'
on conflict (user_niche_id, source_id) do update
set muted = true,
    updated_at = now();

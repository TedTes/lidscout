create table if not exists agent_preferences (
    market_id text primary key references markets(id) on delete cascade,
    preferred_source_families jsonb not null default '[]'::jsonb,
    ignored_themes jsonb not null default '[]'::jsonb,
    ignored_categories jsonb not null default '[]'::jsonb,
    muted_source_ids jsonb not null default '[]'::jsonb,
    extra_instructions text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint agent_preferences_source_families_array
        check (jsonb_typeof(preferred_source_families) = 'array'),
    constraint agent_preferences_ignored_themes_array
        check (jsonb_typeof(ignored_themes) = 'array'),
    constraint agent_preferences_ignored_categories_array
        check (jsonb_typeof(ignored_categories) = 'array'),
    constraint agent_preferences_muted_sources_array
        check (jsonb_typeof(muted_source_ids) = 'array')
);

create index if not exists agent_preferences_updated_at_idx
    on agent_preferences(updated_at desc);

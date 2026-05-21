create table if not exists source_locators (
    id text primary key,
    locator text not null unique,
    enabled boolean not null default true,
    limit_value integer,
    options jsonb not null default '{}'::jsonb,
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint source_locators_locator_not_empty check (btrim(locator) <> ''),
    constraint source_locators_limit_positive check (
        limit_value is null or limit_value >= 1
    )
);

create index if not exists source_locators_enabled_idx
    on source_locators (enabled);

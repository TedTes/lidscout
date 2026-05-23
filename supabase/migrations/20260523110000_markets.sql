create table if not exists markets (
    id text primary key,
    name text not null,
    description text,
    target_user text,
    idea_prompt text,
    created_at timestamptz not null default now(),
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint markets_name_not_empty check (btrim(name) <> '')
);

create index if not exists markets_created_at_idx
    on markets (created_at desc);

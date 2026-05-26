create table if not exists users (
    id          uuid        primary key default gen_random_uuid(),
    email       text        not null unique,
    password_hash text      not null,
    created_at  timestamptz not null default now(),
    constraint users_email_not_empty check (btrim(email) <> '')
);

create index if not exists users_email_idx on users (email);

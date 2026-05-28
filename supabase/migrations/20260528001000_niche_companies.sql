create table if not exists niche_companies (
    id         uuid        primary key default gen_random_uuid(),
    niche_id   uuid        not null references niches (id) on delete cascade,
    name       text        not null,
    website    text,
    is_primary boolean     not null default true,
    created_at timestamptz not null default now(),
    constraint niche_companies_name_not_empty check (btrim(name) <> '')
);

-- Companies are modelled per-niche for MVP simplicity.
-- A company appearing in multiple niches gets duplicate rows.
-- If cross-niche company reuse becomes common, replace with a shared
-- companies table and a niche_companies join table.
create index if not exists niche_companies_niche_id_idx on niche_companies (niche_id);

create type niche_source_health as enum ('unknown', 'active', 'failing', 'paused');

create table if not exists niche_sources (
    id                    uuid               primary key default gen_random_uuid(),
    niche_id              uuid               not null references niches (id) on delete cascade,
    -- null for niche-level sources not tied to a specific tool
    company_id            uuid               references niche_companies (id) on delete cascade,
    locator               text               not null,
    source_type           text               not null,
    source_family         text               not null,
    -- true for gate-free sources (GitHub, HN, Stack Overflow, Discourse).
    -- false for Reddit-when-gated, G2, Capterra (requires proxy or paid API).
    is_gate_free          boolean            not null default false,
    -- set to true only after manual or automated confirmation that this source
    -- contains buyer complaints about the software, not general noise.
    buyer_voice_verified  boolean            not null default false,
    health_status         niche_source_health not null default 'unknown',
    last_scanned_at       timestamptz,
    created_at            timestamptz        not null default now(),
    updated_at            timestamptz        not null default now(),
    constraint niche_sources_locator_not_empty check (btrim(locator) <> '')
);

create index if not exists niche_sources_niche_id_idx   on niche_sources (niche_id);
create index if not exists niche_sources_company_id_idx on niche_sources (company_id);
create unique index if not exists niche_sources_niche_locator_idx on niche_sources (niche_id, locator);

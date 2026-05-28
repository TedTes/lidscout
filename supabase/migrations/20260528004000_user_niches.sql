create table if not exists user_niches (
    id                 uuid         primary key default gen_random_uuid(),
    user_id            uuid         not null references users (id) on delete cascade,
    -- Which shared template this was adopted from. Null for fully custom niches.
    -- Preserved for future "reset to defaults" and "template updated" features.
    -- No update-propagation logic now — just the link.
    -- NOTE: template niches are shared and operator-curated; user_niches are
    -- per-user adoptions that can be customised freely without affecting the
    -- template or other users. Changes to a template affect only future adoptions.
    template_niche_id  uuid         references niches (id) on delete set null,
    -- Copied from template at adoption time, then user-editable
    job                text         not null,
    buyer              text         not null,
    category           text         not null,
    status             niche_status not null default 'defined',
    created_at         timestamptz  not null default now(),
    updated_at         timestamptz  not null default now(),
    -- NOTE (future): templates could be monitored centrally once and findings
    -- served to all adopters, rather than re-monitoring per user. For now each
    -- user_niche monitors independently — simplest correct behaviour.
    constraint user_niches_job_not_empty   check (btrim(job)   <> ''),
    constraint user_niches_buyer_not_empty check (btrim(buyer) <> '')
);

create index if not exists user_niches_user_id_idx          on user_niches (user_id);
create index if not exists user_niches_template_niche_id_idx on user_niches (template_niche_id);

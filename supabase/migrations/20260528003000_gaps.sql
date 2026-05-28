create type unmet_need_type as enum ('time', 'money', 'effort', 'capability', 'fit');

-- signal_strength is computed from breadth + depth + recency + source diversity.
-- It is never assigned by an LLM directly.
create type gap_signal_strength as enum ('weak', 'moderate', 'strong');

create table if not exists gaps (
    id                   uuid               primary key default gen_random_uuid(),
    niche_id             uuid               not null references niches (id) on delete cascade,
    title                text               not null,
    -- synthesized and paraphrased from findings — NOT a template string
    pain_summary         text               not null,
    unmet_need_type      unmet_need_type    not null,
    affected_buyer       text               not null,
    suggested_wedge      text               not null,
    -- breadth: how many of the niche's tools exhibit this gap
    breadth              int                not null default 1,
    -- depth: how many findings support this gap
    depth                int                not null default 1,
    signal_strength      gap_signal_strength not null,
    -- jsonb array of finding ids (from the existing findings/signals table)
    evidence_finding_ids jsonb              not null default '[]',
    created_at           timestamptz        not null default now(),
    updated_at           timestamptz        not null default now(),
    constraint gaps_title_not_empty        check (btrim(title)        <> ''),
    constraint gaps_pain_summary_not_empty check (btrim(pain_summary) <> ''),
    constraint gaps_breadth_positive       check (breadth >= 1),
    constraint gaps_depth_positive         check (depth   >= 1)
);

create index if not exists gaps_niche_id_idx       on gaps (niche_id);
create index if not exists gaps_unmet_need_idx     on gaps (unmet_need_type);
create index if not exists gaps_signal_strength_idx on gaps (signal_strength);

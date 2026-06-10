-- Distinguish operator-curated template niches from user-created custom niches.
-- Custom niches are created on-the-fly via create_market and should not appear
-- in the template picker shown to users.
alter table niches
    add column if not exists is_custom bool not null default false;

-- Mark any niche that has no seeded sources as custom (best-effort cleanup
-- for garbage niches created before this column existed).
update niches n
set is_custom = true
where not exists (
    select 1 from niche_sources ns where ns.niche_id = n.id
)
and (
    -- short or looks like random input (no spaces or < 8 chars)
    length(btrim(n.job)) < 8
    or position(' ' in btrim(n.job)) = 0
);

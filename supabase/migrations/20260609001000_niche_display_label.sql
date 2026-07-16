-- Add display_label to niches for short sidebar labels.
-- Falls back to a truncated job field when null.
alter table niches
    add column if not exists display_label text;

-- Populate display labels by truncating job to 32 chars as a reasonable default.
update niches
set display_label = left(btrim(job), 32)
where display_label is null;

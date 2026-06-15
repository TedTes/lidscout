-- Retire the legacy niche-scoped source tables after runtime reads/writes moved
-- to sources, template_sources, user_sources, and user_source_run_stats.

alter table if exists findings
    drop constraint if exists findings_source_id_fkey;

-- Older findings may still point at niche_sources.id. Preserve provenance by
-- remapping those ids to the canonical source row created from the same
-- source_type + locator before the legacy table is dropped.
do $$
begin
    if to_regclass('public.findings') is not null
       and to_regclass('public.niche_sources') is not null
       and to_regclass('public.sources') is not null then
        update findings f
        set source_id = s.id
        from niche_sources ns
        join sources s
          on s.source_type = ns.source_type
         and s.locator = ns.locator
        where f.source_id = ns.id;
    end if;
end $$;

-- If any historical finding points at a source row that could not be migrated,
-- keep the finding and clear only the invalid source reference.
do $$
begin
    if to_regclass('public.findings') is not null
       and to_regclass('public.sources') is not null then
        update findings f
        set source_id = null
        where f.source_id is not null
          and not exists (
              select 1
              from sources s
              where s.id = f.source_id
          );
    end if;
end $$;

do $$
begin
    if to_regclass('public.findings') is not null
    and to_regclass('public.sources') is not null
    and not exists (
        select 1
        from pg_constraint
        where conname = 'findings_source_id_fkey'
          and conrelid = 'public.findings'::regclass
    ) then
        alter table findings
            add constraint findings_source_id_fkey
            foreign key (source_id) references sources(id) on delete set null;
    end if;
end $$;

drop table if exists niche_source_health_stats;
drop table if exists niche_sources;

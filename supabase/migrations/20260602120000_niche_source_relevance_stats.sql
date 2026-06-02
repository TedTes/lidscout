alter table niche_source_health_stats
    add column if not exists rule_filtered_count integer not null default 0,
    add column if not exists llm_filtered_count integer not null default 0,
    add column if not exists relevance_failed_count integer not null default 0,
    add column if not exists last_rule_filtered_count integer not null default 0,
    add column if not exists last_llm_filtered_count integer not null default 0,
    add column if not exists last_relevance_failed_count integer not null default 0,
    add column if not exists rejection_breakdown jsonb not null default '{}'::jsonb,
    add column if not exists last_rejection_breakdown jsonb not null default '{}'::jsonb;

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conname = 'niche_source_health_stats_relevance_counts_non_negative'
    ) then
        alter table niche_source_health_stats
            add constraint niche_source_health_stats_relevance_counts_non_negative check (
                rule_filtered_count >= 0
                and llm_filtered_count >= 0
                and relevance_failed_count >= 0
                and last_rule_filtered_count >= 0
                and last_llm_filtered_count >= 0
                and last_relevance_failed_count >= 0
            );
    end if;
end $$;

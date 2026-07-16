-- Remove broad legacy built-in templates that do not fit the current core loop.
-- Custom user-created watchlists are preserved. Adopted copies of the removed
-- built-in templates are deleted so the app does not keep showing stale examples.

with kept(job) as (
    values
        ('Track customer complaints about internal tool builders'),
        ('Track customer complaints about managed Postgres platforms'),
        ('Track customer complaints about feature flag platforms'),
        ('Track customer complaints about API development tools'),
        ('Track customer complaints about podcast hosting platforms')
),
obsolete_templates as (
    select n.id
    from niches n
    where n.is_custom = false
      and not exists (
          select 1
          from kept
          where lower(btrim(kept.job)) = lower(btrim(n.job))
      )
)
delete from user_niches un
using obsolete_templates ot
where un.template_niche_id = ot.id;

with kept(job) as (
    values
        ('Track customer complaints about internal tool builders'),
        ('Track customer complaints about managed Postgres platforms'),
        ('Track customer complaints about feature flag platforms'),
        ('Track customer complaints about API development tools'),
        ('Track customer complaints about podcast hosting platforms')
)
delete from niches n
where n.is_custom = false
  and not exists (
      select 1
      from kept
      where lower(btrim(kept.job)) = lower(btrim(n.job))
  );

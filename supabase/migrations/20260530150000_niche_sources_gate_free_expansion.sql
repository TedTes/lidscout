-- Add more concrete gate-free high-signal sources.
--
-- This migration intentionally avoids gated/proxy/manual sources. It adds only
-- structured API URLs that the current worker can fetch today:
--   - GitHub issue search API rows derived from existing GitHub repo issue URLs.
--   - StackOverflow search rows for technical/operator-heavy niches.

-- GitHub browser issue pages are useful for humans, but the worker gets cleaner
-- structured data from the search API. Keep existing rows; add API equivalents.
insert into niche_sources (
    niche_id,
    company_id,
    locator,
    source_type,
    source_family,
    is_gate_free,
    enabled,
    options,
    tier,
    signal_quality_score,
    access_mode,
    recommended_cadence
)
select distinct
    niche_id,
    company_id,
    'https://api.github.com/search/issues?q=repo:'
        || regexp_replace(locator, '^https://github.com/([^/]+/[^/]+)/issues/?$', '\1')
        || '+is%3Aissue&sort=updated&order=desc',
    'github_issues_search',
    'technical_forum',
    true,
    true,
    '{"adapter":"json","items_path":"items","source_family":"technical_forum"}'::jsonb,
    1,
    0.95,
    'api',
    'daily'
from niche_sources
where locator ~ '^https://github.com/[^/]+/[^/]+/issues/?$'
on conflict (niche_id, locator) do nothing;

-- Prefer the structured API rows above over browser HTML issue pages.
update niche_sources
set
    enabled = false,
    access_mode = 'html',
    options = coalesce(options, '{}'::jsonb)
        || '{"replaced_by":"github_issues_search"}'::jsonb
where locator ~ '^https://github.com/[^/]+/[^/]+/issues/?$'
  and source_type = 'github_issues';

-- Add niche-level StackOverflow search for categories where practitioner
-- questions often reveal implementation friction and unmet needs.
insert into niche_sources (
    niche_id,
    locator,
    source_type,
    source_family,
    is_gate_free,
    enabled,
    options,
    tier,
    signal_quality_score,
    access_mode,
    recommended_cadence
)
select
    id,
    'https://api.stackexchange.com/2.3/search/advanced?q='
        || trim(both '+' from regexp_replace(lower(job), '[^a-z0-9]+', '+', 'g'))
        || '&site=stackoverflow&order=desc&sort=creation&pagesize=25',
    'stackoverflow_search',
    'technical_forum',
    true,
    true,
    '{"adapter":"json","items_path":"items","source_family":"technical_forum"}'::jsonb,
    1,
    0.95,
    'api',
    'daily'
from niches
where category in ('devtools', 'data', 'automation', 'no_code')
on conflict (niche_id, locator) do nothing;

-- Make sure any existing GitHub API rows have the JSON parser hint needed by
-- JsonUrlAdapter.
update niche_sources
set
    options = coalesce(options, '{}'::jsonb)
        || '{"adapter":"json","items_path":"items","source_family":"technical_forum"}'::jsonb,
    source_family = 'technical_forum',
    is_gate_free = true,
    enabled = true,
    tier = coalesce(tier, 1),
    signal_quality_score = coalesce(signal_quality_score, 0.95),
    access_mode = 'api',
    recommended_cadence = coalesce(recommended_cadence, 'daily')
where source_type = 'github_issues_search';

update niche_sources
set
    options = coalesce(options, '{}'::jsonb)
        || '{"adapter":"json","items_path":"items","source_family":"technical_forum"}'::jsonb,
    source_family = 'technical_forum',
    is_gate_free = true,
    enabled = true,
    tier = coalesce(tier, 1),
    signal_quality_score = coalesce(signal_quality_score, 0.95),
    access_mode = 'api',
    recommended_cadence = coalesce(recommended_cadence, 'daily')
where source_type in ('stackoverflow', 'stackoverflow_search');

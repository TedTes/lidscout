-- Add scan-ready public sources for the podcast hosting template.
--
-- Reddit remains gated until OAuth support is configured. These additions use
-- JSON APIs that the current worker can scan without auth or proxy support.

with source_seed (
    locator,
    source_type,
    source_family,
    is_gate_free,
    access_mode,
    requires_proxy,
    requires_auth,
    default_options,
    tier,
    signal_quality_score,
    recommended_cadence,
    default_limit_value
) as (
    values
        (
            'https://api.github.com/search/issues?q=repo:Podcastindex-org/podcast-namespace+is%3Aissue&sort=updated&order=desc',
            'github_issues_search',
            'technical_forum',
            true,
            'api',
            false,
            false,
            '{"adapter": "json", "items_path": "items", "source_family": "technical_forum"}'::jsonb,
            1,
            0.95,
            'daily',
            25
        ),
        (
            'https://api.github.com/search/issues?q=repo:podlove/podlove-publisher+is%3Aissue&sort=updated&order=desc',
            'github_issues_search',
            'technical_forum',
            true,
            'api',
            false,
            false,
            '{"adapter": "json", "items_path": "items", "source_family": "technical_forum"}'::jsonb,
            1,
            0.95,
            'daily',
            25
        ),
        (
            'https://api.stackexchange.com/2.3/search/advanced?q=podcast+rss+feed+hosting+audio&site=stackoverflow&order=desc&sort=creation&pagesize=25',
            'stackoverflow_search',
            'technical_forum',
            true,
            'api',
            false,
            false,
            '{"adapter": "json", "items_path": "items", "source_family": "technical_forum"}'::jsonb,
            1,
            0.95,
            'daily',
            25
        ),
        (
            'https://api.stackexchange.com/2.3/search/advanced?q=podcast+upload+audio+transcription&site=stackoverflow&order=desc&sort=creation&pagesize=25',
            'stackoverflow_search',
            'technical_forum',
            true,
            'api',
            false,
            false,
            '{"adapter": "json", "items_path": "items", "source_family": "technical_forum"}'::jsonb,
            1,
            0.95,
            'daily',
            25
        )
),
inserted_sources as (
    insert into sources (
        locator,
        source_type,
        source_family,
        is_gate_free,
        access_mode,
        requires_proxy,
        requires_auth
    )
    select
        locator,
        source_type,
        source_family,
        is_gate_free,
        access_mode,
        requires_proxy,
        requires_auth
    from source_seed
    on conflict (source_type, locator) do update
    set source_family = excluded.source_family,
        is_gate_free = excluded.is_gate_free,
        access_mode = excluded.access_mode,
        requires_proxy = excluded.requires_proxy,
        requires_auth = excluded.requires_auth,
        updated_at = now()
    returning id, locator, source_type
),
podcast_template as (
    select id
    from niches
    where job = 'Produce and host a podcast'
      and is_custom = false
    limit 1
),
inserted_bindings as (
    insert into template_sources (
        template_niche_id,
        source_id,
        default_enabled,
        default_limit_value,
        default_scan_frequency,
        default_buyer_voice_verified,
        default_options,
        tier,
        signal_quality_score,
        recommended_cadence
    )
    select
        podcast_template.id,
        inserted_sources.id,
        true,
        source_seed.default_limit_value,
        source_seed.recommended_cadence,
        false,
        source_seed.default_options,
        source_seed.tier,
        source_seed.signal_quality_score,
        source_seed.recommended_cadence
    from podcast_template
    join inserted_sources
      on true
    join source_seed
      on source_seed.source_type = inserted_sources.source_type
     and source_seed.locator = inserted_sources.locator
    on conflict (template_niche_id, source_id) do update
    set default_enabled = true,
        default_limit_value = excluded.default_limit_value,
        default_scan_frequency = excluded.default_scan_frequency,
        default_options = excluded.default_options,
        tier = excluded.tier,
        signal_quality_score = excluded.signal_quality_score,
        recommended_cadence = excluded.recommended_cadence,
        updated_at = now()
    returning id, template_niche_id, source_id, default_limit_value,
        default_scan_frequency, default_options, tier
)
insert into user_sources (
    user_niche_id,
    source_id,
    template_source_binding_id,
    enabled,
    muted,
    cadence,
    priority,
    limit_value,
    options
)
select
    user_niches.id,
    inserted_bindings.source_id,
    inserted_bindings.id,
    true,
    false,
    inserted_bindings.default_scan_frequency,
    inserted_bindings.tier,
    inserted_bindings.default_limit_value,
    inserted_bindings.default_options
from user_niches
join inserted_bindings
  on inserted_bindings.template_niche_id = user_niches.template_niche_id
on conflict (user_niche_id, source_id) do update
set template_source_binding_id = coalesce(
        user_sources.template_source_binding_id,
        excluded.template_source_binding_id
    ),
    enabled = excluded.enabled,
    muted = false,
    cadence = excluded.cadence,
    priority = excluded.priority,
    limit_value = excluded.limit_value,
    options = case
        when user_sources.options = '{}'::jsonb then excluded.options
        else user_sources.options
    end,
    updated_at = now();

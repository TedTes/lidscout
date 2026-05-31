-- Add source-catalog controls so high-signal sources can be stored without
-- every candidate being actively fetched by the worker.

alter table niche_sources
    add column if not exists tier integer,
    add column if not exists signal_quality_score double precision,
    add column if not exists access_mode text not null default 'unknown',
    add column if not exists requires_proxy boolean not null default false,
    add column if not exists requires_auth boolean not null default false,
    add column if not exists recommended_cadence text;

alter table niche_sources
    add constraint niche_sources_tier_range
        check (tier is null or tier between 1 and 6);

alter table niche_sources
    add constraint niche_sources_signal_quality_range
        check (
            signal_quality_score is null
            or (signal_quality_score >= 0 and signal_quality_score <= 1)
        );

alter table niche_sources
    add constraint niche_sources_access_mode_check
        check (
            access_mode in (
                'unknown',
                'api',
                'api_auth',
                'json',
                'rss',
                'html',
                'proxy_required',
                'manual'
            )
        );

-- Normalize broad families so source grouping and monitorability scoring do not
-- treat HN/StackOverflow search as a separate family from technical forums.
update niche_sources
set source_family = 'technical_forum'
where source_type in (
    'hackernews',
    'hackernews_search',
    'stackoverflow',
    'stackoverflow_search',
    'github_issues',
    'github_discussions',
    'discourse',
    'discourse_forum'
);

update niche_sources
set
    access_mode = case
        when source_type in ('github_issues', 'github_discussions') then 'api'
        when source_type in ('hackernews', 'hackernews_search') then 'api'
        when source_type in ('stackoverflow', 'stackoverflow_search') then 'api'
        when source_type in ('discourse', 'discourse_forum') then 'json'
        when source_type in ('reddit', 'reddit_search', 'reddit_subreddit') then 'api_auth'
        when source_type in ('g2', 'g2_reviews', 'capterra', 'capterra_reviews', 'trust_radius', 'trustpilot', 'review_search') then 'proxy_required'
        when source_type in ('rss', 'changelog') then 'rss'
        when source_type in ('public_roadmap', 'canny', 'productboard') then 'html'
        else access_mode
    end,
    requires_auth = case
        when source_type in ('reddit', 'reddit_search', 'reddit_subreddit') then true
        else requires_auth
    end,
    requires_proxy = case
        when source_type in ('g2', 'g2_reviews', 'capterra', 'capterra_reviews', 'trust_radius', 'trustpilot', 'review_search') then true
        else requires_proxy
    end,
    tier = case
        when source_type in ('github_issues', 'github_discussions', 'stackoverflow', 'stackoverflow_search') then 1
        when source_type in ('discourse', 'discourse_forum', 'reddit', 'reddit_search', 'reddit_subreddit', 'hackernews', 'hackernews_search') then 2
        when source_type in ('app_store', 'play_store', 'producthunt', 'indiehackers') then 3
        when source_type in ('trade_forum', 'vertical_forum', 'forum') then 4
        when source_type in ('rss', 'changelog', 'pricing_page', 'jobs', 'public_roadmap', 'canny', 'productboard') then 5
        else tier
    end,
    signal_quality_score = case
        when source_type in ('github_issues', 'github_discussions', 'stackoverflow', 'stackoverflow_search') then 0.95
        when source_type in ('g2', 'g2_reviews', 'capterra', 'capterra_reviews', 'trust_radius') then 0.9
        when source_type in ('discourse', 'discourse_forum', 'reddit', 'reddit_search', 'reddit_subreddit') then 0.82
        when source_type in ('hackernews', 'hackernews_search') then 0.78
        when source_type in ('app_store', 'play_store', 'producthunt', 'indiehackers') then 0.68
        when source_type in ('rss', 'changelog', 'public_roadmap', 'canny', 'productboard') then 0.55
        else signal_quality_score
    end,
    recommended_cadence = case
        when source_type in ('github_issues', 'github_discussions', 'stackoverflow', 'stackoverflow_search', 'hackernews', 'hackernews_search', 'discourse', 'discourse_forum') then 'daily'
        when source_type in ('rss', 'changelog', 'pricing_page', 'jobs') then 'weekly'
        else recommended_cadence
    end;

-- Cataloguing a source is not the same thing as being able to fetch it today.
-- Keep gated/proxy-required sources available in setup UI, but stop workers
-- from repeatedly hitting known-bad endpoints until support is explicitly added.
update niche_sources
set enabled = false
where requires_proxy = true
   or requires_auth = true
   or is_gate_free = false;

create index if not exists niche_sources_enabled_quality_idx
    on niche_sources (enabled, tier, signal_quality_score desc);

create index if not exists niche_sources_access_mode_idx
    on niche_sources (access_mode);

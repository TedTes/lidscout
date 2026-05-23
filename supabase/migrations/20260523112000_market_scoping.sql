alter table competitors
    add column if not exists market_id text references markets(id) on delete set null;

create index if not exists competitors_market_idx
    on competitors (market_id);

alter table monitored_sources
    add column if not exists market_id text references markets(id) on delete cascade;

alter table monitored_sources
    alter column competitor_id drop not null;

create index if not exists monitored_sources_market_enabled_idx
    on monitored_sources (market_id, enabled);

alter table signal_evidence
    add column if not exists market_id text references markets(id) on delete set null;

create index if not exists signal_evidence_market_detected_at_idx
    on signal_evidence (market_id, detected_at desc);

-- Add evidence_signature to opportunities for synthesis change detection.
-- Stores a short hash of the sorted finding IDs at last synthesis time.
-- Pipeline skips re-synthesis when this matches the current finding set.

alter table if exists opportunities
    add column if not exists evidence_signature text;

comment on column opportunities.evidence_signature is
    'SHA-256 prefix of pipe-joined sorted finding IDs at last synthesis. '
    'Unchanged signature means no new evidence; synthesis is skipped.';

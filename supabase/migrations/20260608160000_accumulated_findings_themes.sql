create extension if not exists vector with schema extensions;

create table if not exists findings (
    id                         uuid primary key default gen_random_uuid(),
    user_niche_id              uuid not null references user_niches (id) on delete cascade,
    niche_id                   uuid references niches (id) on delete set null,
    source_id                  uuid references niche_sources (id) on delete set null,
    company_id                 uuid references niche_companies (id) on delete set null,
    post_id                    text not null references posts (id) on delete cascade,
    post_title                 text,
    source_url                 text,
    evidence_url               text,
    evidence_text              text not null,
    pain                       text not null,
    affected_user              text,
    job_to_be_done             text,
    current_workaround         text,
    category                   text,
    urgency                    text not null,
    severity                   text not null,
    willingness_to_pay         boolean,
    confidence                 double precision not null default 0,
    detected_at                timestamptz,
    extracted_at               timestamptz not null default now(),
    pipeline_run_id            text,
    structured_embedding_text  text not null,
    embedding                  vector(1536),
    metadata                   jsonb not null default '{}'::jsonb,
    constraint findings_pain_not_empty check (btrim(pain) <> ''),
    constraint findings_evidence_text_not_empty check (btrim(evidence_text) <> ''),
    constraint findings_embedding_text_not_empty check (btrim(structured_embedding_text) <> ''),
    constraint findings_urgency_value check (urgency in ('low', 'medium', 'high')),
    constraint findings_severity_value check (severity in ('low', 'medium', 'high')),
    constraint findings_confidence_range check (confidence >= 0 and confidence <= 1),
    constraint findings_unique_user_post unique (user_niche_id, post_id)
);

create index if not exists findings_user_niche_id_idx
    on findings (user_niche_id);

create index if not exists findings_source_id_idx
    on findings (source_id);

create index if not exists findings_company_id_idx
    on findings (company_id);

create index if not exists findings_detected_at_idx
    on findings (detected_at desc);

create index if not exists findings_embedding_hnsw_idx
    on findings using hnsw (embedding vector_cosine_ops)
    where embedding is not null;

create table if not exists themes (
    id                         uuid primary key default gen_random_uuid(),
    user_niche_id              uuid not null references user_niches (id) on delete cascade,
    niche_id                   uuid references niches (id) on delete set null,
    title                      text not null,
    summary                    text not null,
    status                     text not null default 'emerging',
    qualification_reason       text,
    finding_count              integer not null default 0,
    source_count               integer not null default 0,
    company_count              integer not null default 0,
    average_confidence         double precision not null default 0,
    latest_finding_at          timestamptz,
    last_qualified_at          timestamptz,
    last_synthesized_at        timestamptz,
    centroid_embedding         vector(1536),
    created_at                 timestamptz not null default now(),
    updated_at                 timestamptz not null default now(),
    metadata                   jsonb not null default '{}'::jsonb,
    constraint themes_title_not_empty check (btrim(title) <> ''),
    constraint themes_summary_not_empty check (btrim(summary) <> ''),
    constraint themes_status_value check (
        status in ('emerging', 'qualified', 'rejected', 'archived')
    ),
    constraint themes_counts_non_negative check (
        finding_count >= 0
        and source_count >= 0
        and company_count >= 0
    ),
    constraint themes_average_confidence_range check (
        average_confidence >= 0 and average_confidence <= 1
    )
);

create index if not exists themes_user_niche_status_idx
    on themes (user_niche_id, status);

create index if not exists themes_latest_finding_at_idx
    on themes (latest_finding_at desc);

create index if not exists themes_centroid_embedding_hnsw_idx
    on themes using hnsw (centroid_embedding vector_cosine_ops)
    where centroid_embedding is not null;

create table if not exists theme_findings (
    theme_id                   uuid not null references themes (id) on delete cascade,
    finding_id                 uuid not null references findings (id) on delete cascade,
    assigned_at                timestamptz not null default now(),
    assignment_method          text not null,
    similarity_score           double precision,
    llm_decision               jsonb,
    metadata                   jsonb not null default '{}'::jsonb,
    primary key (theme_id, finding_id),
    constraint theme_findings_assignment_method_check check (
        assignment_method in (
            'auto_high_confidence',
            'auto_borderline_llm',
            'seed_new_theme',
            'manual'
        )
    ),
    constraint theme_findings_similarity_range check (
        similarity_score is null
        or (similarity_score >= -1 and similarity_score <= 1)
    )
);

create index if not exists theme_findings_finding_id_idx
    on theme_findings (finding_id);

create index if not exists theme_findings_assignment_method_idx
    on theme_findings (assignment_method);

alter table if exists opportunities
    add column if not exists source_theme_id uuid references themes (id) on delete set null;

alter table if exists opportunities
    add column if not exists last_resynthesized_at timestamptz;

create index if not exists opportunities_source_theme_id_idx
    on opportunities (source_theme_id);

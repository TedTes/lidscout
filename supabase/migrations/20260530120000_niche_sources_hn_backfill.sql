-- Populate HackerNews Algolia search sources for templates that have none or only one.
-- Uses subqueries on niches.job so UUIDs don't need to be hardcoded.
-- All rows are is_gate_free=true; ON CONFLICT DO NOTHING is safe to re-run.
-- Remove any previously inserted tags=story rows (story titles → low pain signal yield).
delete from niche_sources where locator like '%hn.algolia.com%tags=story%';

-- ── Nonprofit CRM ─────────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=bloomerang+nonprofit&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage members and donors for a nonprofit'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=donorbox+fundraising&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage members and donors for a nonprofit'
on conflict (niche_id, locator) do nothing;

-- ── General project management ────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=monday.com+clickup&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage general team projects and tasks'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=asana+project+management&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage general team projects and tasks'
on conflict (niche_id, locator) do nothing;

-- ── HRIS ──────────────────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=rippling+deel&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage employee records (HRIS)'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=bamboohr+hris&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage employee records (HRIS)'
on conflict (niche_id, locator) do nothing;

-- ── ATS ───────────────────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=greenhouse+lever+recruiting&tags=comment', 'hackernews', 'search', true
from niches where job = 'Track and hire job applicants (ATS)'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=ashby+hiring&tags=comment', 'hackernews', 'search', true
from niches where job = 'Track and hire job applicants (ATS)'
on conflict (niche_id, locator) do nothing;

-- ── Payroll ───────────────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=gusto+payroll&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run payroll for a small business'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=rippling+payroll&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run payroll for a small business'
on conflict (niche_id, locator) do nothing;

-- ── Bookkeeping ───────────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=quickbooks+xero&tags=comment', 'hackernews', 'search', true
from niches where job = 'Do small-business bookkeeping and accounting'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=freshbooks+accounting&tags=comment', 'hackernews', 'search', true
from niches where job = 'Do small-business bookkeeping and accounting'
on conflict (niche_id, locator) do nothing;

-- ── Gym management ────────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=mindbody+gym+software&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage gym memberships and bookings'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=pushpress+wodify&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage gym memberships and bookings'
on conflict (niche_id, locator) do nothing;

-- ── Restaurant POS ────────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=toast+restaurant+pos&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run a restaurant POS and operations'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=square+restaurant&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run a restaurant POS and operations'
on conflict (niche_id, locator) do nothing;

-- ── Short-term rentals ────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=guesty+airbnb+management&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage short-term rentals (Airbnb, VRBO)'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=hospitable+short+term+rental&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage short-term rentals (Airbnb, VRBO)'
on conflict (niche_id, locator) do nothing;

-- ── Long-term rental ──────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=appfolio+buildium+property&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage long-term rental property'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=doorloop+property+management&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage long-term rental property'
on conflict (niche_id, locator) do nothing;

-- ── Real estate CRM ───────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=follow+up+boss+real+estate&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage real estate leads and transactions'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=kvcore+real+estate+crm&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage real estate leads and transactions'
on conflict (niche_id, locator) do nothing;

-- ── Construction ──────────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=procore+construction&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage construction projects and bids'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=buildertrend+jobsite&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage construction projects and bids'
on conflict (niche_id, locator) do nothing;

-- ── Field service (HVAC, plumbing, electrical) ────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=servicetitan+hvac&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run a home field-service business (HVAC, plumbing, electrical)'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=jobber+field+service&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run a home field-service business (HVAC, plumbing, electrical)'
on conflict (niche_id, locator) do nothing;

-- ── Dental practice ───────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=dentrix+open+dental&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run a dental practice'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=dental+practice+software&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run a dental practice'
on conflict (niche_id, locator) do nothing;

-- ── Therapy practice (EHR) ────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=simplepractice+therapy&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run a solo therapy practice (EHR and billing)'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=therapynotes+ehr&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run a solo therapy practice (EHR and billing)'
on conflict (niche_id, locator) do nothing;

-- ── Contract lifecycle (CLM) ──────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=ironclad+contracts&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage the contract lifecycle (CLM)'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=juro+contract+management&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage the contract lifecycle (CLM)'
on conflict (niche_id, locator) do nothing;

-- ── Law firm ──────────────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=clio+law+firm&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run a small law firm (case management and billing)'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=mycase+legal+software&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run a small law firm (case management and billing)'
on conflict (niche_id, locator) do nothing;

-- ── SEO ───────────────────────────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=semrush+seo&tags=comment', 'hackernews', 'search', true
from niches where job = 'Do keyword research and track SEO rankings'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=ahrefs+seo&tags=comment', 'hackernews', 'search', true
from niches where job = 'Do keyword research and track SEO rankings'
on conflict (niche_id, locator) do nothing;

-- ── Social media scheduling ───────────────────────────────────────────────────
insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=buffer+social+media&tags=comment', 'hackernews', 'search', true
from niches where job = 'Schedule and publish social media posts'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=hootsuite+scheduling&tags=comment', 'hackernews', 'search', true
from niches where job = 'Schedule and publish social media posts'
on conflict (niche_id, locator) do nothing;

-- ── Templates with only 1 HN source — add a second ───────────────────────────

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=shipbob+fulfillment&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage ecommerce fulfillment and shipping'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=helium10+jungle+scout&tags=comment', 'hackernews', 'search', true
from niches where job = 'Research and manage Amazon FBA products'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=capcut+video+editing&tags=comment', 'hackernews', 'search', true
from niches where job = 'Edit video for social and marketing'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=framer+uxpin+design&tags=comment', 'hackernews', 'search', true
from niches where job = 'Design UI/UX interfaces and prototypes'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=expensify+ramp+expense&tags=comment', 'hackernews', 'search', true
from niches where job = 'Manage company spend and corporate cards'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=document360+helpjuice&tags=comment', 'hackernews', 'search', true
from niches where job = 'Build a self-serve help center and knowledge base'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=lemlist+instantly+email&tags=comment', 'hackernews', 'search', true
from niches where job = 'Run cold-email outreach sequences at scale'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=dagster+prefect+pipeline&tags=comment', 'hackernews', 'search', true
from niches where job = 'Orchestrate data pipelines'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=airbyte+fivetran+elt&tags=comment', 'hackernews', 'search', true
from niches where job = 'Ingest and sync source data into a warehouse (ELT)'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=sqlmesh+dbt+transform&tags=comment', 'hackernews', 'search', true
from niches where job = 'Transform data in the warehouse (analytics engineering)'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=tableau+power+bi&tags=comment', 'hackernews', 'search', true
from niches where job = 'Build BI dashboards on a database'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=n8n+make+automation&tags=comment', 'hackernews', 'search', true
from niches where job = 'Automate workflows between SaaS apps'
on conflict (niche_id, locator) do nothing;

insert into niche_sources (niche_id, locator, source_type, source_family, is_gate_free)
select id, 'https://hn.algolia.com/api/v1/search_by_date?query=appsmith+budibase+retool&tags=comment', 'hackernews', 'search', true
from niches where job = 'Build internal tools and admin panels over a database'
on conflict (niche_id, locator) do nothing;

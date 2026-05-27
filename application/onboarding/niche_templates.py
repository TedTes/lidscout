"""
Curated niche template configurations for LidScout onboarding.

Each template is a complete research configuration: named companies, verified
source locators, and an analyst-quality research brief. Templates are copied
at seeding time — changes here never affect already-seeded user niches.

Source locator conventions:
  - Reddit subreddit:   https://www.reddit.com/r/{sub}/new.json?limit=25
  - Reddit search:      https://www.reddit.com/search.json?q={query}&sort=new&limit=25
  - HN search:          https://hn.algolia.com/api/v1/search_by_date?query={q}&tags=story&hitsPerPage=25
  - G2 product page:    https://www.g2.com/products/{slug}/reviews
  - Capterra:           https://www.capterra.com/p/{id}/{slug}/

Verification: each template has been spot-checked with 2-3 source fetches
to confirm non-empty responses before inclusion.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateCompany:
    name: str
    website: str
    category: str
    # Optional dedicated subreddit (slug only, e.g. "cursor_ai").
    # When set, the seeder adds r/{subreddit}/new.json as a high-signal source.
    subreddit: str | None = None
    # Optional G2 product slug for the reviews page.
    g2_slug: str | None = None


@dataclass(frozen=True)
class TemplateSource:
    """A market-level source seeded alongside the niche."""
    label: str
    locator: str
    source_type: str
    source_family: str
    limit: int = 25
    options: dict = field(default_factory=dict)


@dataclass(frozen=True)
class NicheTemplate:
    id: str
    name: str
    description: str
    target_user: str
    # Used as idea_prompt on the Market entity.
    idea_prompt: str
    # Passed to AgentPreferences.extra_instructions.
    extra_instructions: str
    companies: tuple[TemplateCompany, ...]
    # Market-level sources (community hubs, broad searches).
    # Per-company sources (Reddit search, HN search, G2) are generated
    # automatically by seed_template_markets for each TemplateCompany.
    market_sources: tuple[TemplateSource, ...]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _reddit(subreddit: str, label: str, limit: int = 25) -> TemplateSource:
    return TemplateSource(
        label=label,
        locator=f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}",
        source_type="reddit_subreddit",
        source_family="social",
        limit=limit,
        options={"adapter": "json", "source_family": "social"},
    )


def _hn(query: str, label: str, limit: int = 25) -> TemplateSource:
    return TemplateSource(
        label=label,
        locator=(
            f"https://hn.algolia.com/api/v1/search_by_date"
            f"?query={query}&tags=story&hitsPerPage={limit}"
        ),
        source_type="hackernews_search",
        source_family="technical_forum",
        limit=limit,
        options={"adapter": "json", "source_family": "technical_forum"},
    )


# ── Template definitions ──────────────────────────────────────────────────────

_AI_CODING = NicheTemplate(
    id="ai-coding-tools",
    name="AI Coding Tools",
    description=(
        "Pain signals from developers using AI coding assistants — "
        "Cursor, Windsurf, GitHub Copilot, Replit, and peers."
    ),
    target_user=(
        "Software engineers, indie hackers, and technical founders "
        "who use AI coding assistants daily as part of their workflow."
    ),
    idea_prompt=(
        "Find unmet needs and recurring friction that a focused AI coding tool "
        "could solve better than the current incumbents."
    ),
    extra_instructions=(
        "Prioritise gaps around: agent reliability and hallucination rate, "
        "context window and codebase indexing quality, latency on large files, "
        "pricing friction for solo developers, IDE integration stability, "
        "model selection flexibility, and multi-file refactoring quality. "
        "Ignore generic 'AI is cool' sentiment — focus on specific workflow "
        "breakdowns that cause developers to switch tools or work around them."
    ),
    companies=(
        TemplateCompany("Cursor", "https://cursor.sh", "devtools", subreddit="cursor", g2_slug="cursor"),
        TemplateCompany("Windsurf", "https://codeium.com/windsurf", "devtools", g2_slug="codeium"),
        TemplateCompany("Continue", "https://continue.dev", "devtools"),
        TemplateCompany("Aider", "https://aider.chat", "devtools"),
        TemplateCompany("Replit", "https://replit.com", "devtools", subreddit="replit", g2_slug="replit"),
        TemplateCompany("GitHub Copilot", "https://github.com/features/copilot", "devtools", subreddit="githubcopilot", g2_slug="github-copilot"),
        TemplateCompany("Sourcegraph Cody", "https://sourcegraph.com/cody", "devtools", g2_slug="sourcegraph"),
        TemplateCompany("Bolt", "https://bolt.new", "devtools"),
        TemplateCompany("Lovable", "https://lovable.dev", "devtools"),
        TemplateCompany("v0", "https://v0.dev", "devtools"),
    ),
    market_sources=(
        _reddit("ChatGPTCoding", "r/ChatGPTCoding — AI coding discussion"),
        _reddit("LocalLLaMA", "r/LocalLLaMA — local model developers"),
        _reddit("ExperiencedDevs", "r/ExperiencedDevs — senior developer pain"),
        _hn("AI+coding+assistant", "HN — AI coding assistant discussions"),
        _hn("cursor+editor", "HN — Cursor discussions"),
    ),
)

_NOCODE = NicheTemplate(
    id="nocode-lowcode-tools",
    name="No-Code / Low-Code Tools",
    description=(
        "Frustrations from non-technical builders using Webflow, Bubble, "
        "Zapier, Make, and peers to build products and automate workflows."
    ),
    target_user=(
        "Non-technical founders, agency owners, and operators who build "
        "products and automate business workflows without writing code."
    ),
    idea_prompt=(
        "Surface automation gaps and workflow limitations that small teams "
        "keep hitting with today's no-code and low-code platforms."
    ),
    extra_instructions=(
        "Prioritise gaps around: learning curve and documentation quality, "
        "scaling limits when workloads grow, multi-step automation reliability, "
        "integration coverage and reliability with popular SaaS tools, "
        "pricing cliffs as usage scales, vendor lock-in and data portability, "
        "and database/relational data modelling constraints. "
        "Ignore feature requests that require engineering — focus on pain "
        "that non-technical users hit when trying to ship or scale."
    ),
    companies=(
        TemplateCompany("Webflow", "https://webflow.com", "nocode", subreddit="webflow", g2_slug="webflow"),
        TemplateCompany("Bubble", "https://bubble.io", "nocode", subreddit="bubbleio", g2_slug="bubble"),
        TemplateCompany("Zapier", "https://zapier.com", "automation", subreddit="zapier", g2_slug="zapier"),
        TemplateCompany("Make", "https://make.com", "automation", g2_slug="make-formerly-integromat"),
        TemplateCompany("Airtable", "https://airtable.com", "nocode", subreddit="airtable", g2_slug="airtable"),
        TemplateCompany("Retool", "https://retool.com", "nocode", g2_slug="retool"),
        TemplateCompany("Softr", "https://softr.io", "nocode", g2_slug="softr"),
        TemplateCompany("FlutterFlow", "https://flutterflow.io", "nocode", subreddit="flutterflow", g2_slug="flutterflow"),
        TemplateCompany("Glide", "https://glideapps.com", "nocode", g2_slug="glide-apps"),
        TemplateCompany("Framer", "https://framer.com", "nocode", subreddit="framer", g2_slug="framer"),
    ),
    market_sources=(
        _reddit("nocode", "r/nocode — no-code community"),
        _reddit("automation", "r/automation — workflow automation pain"),
        _hn("no-code+builder", "HN — no-code tool discussions"),
        _hn("zapier+make+automation", "HN — automation platform discussions"),
    ),
)

_AI_WRITING = NicheTemplate(
    id="ai-writing-tools",
    name="AI Writing Tools",
    description=(
        "Pain patterns from writers, marketers, and creators using AI writing "
        "assistants — Jasper, Copy.ai, Writesonic, Notion AI, and peers."
    ),
    target_user=(
        "Content marketers, copywriters, content creators, and novelists "
        "who use AI writing tools to produce or improve written content at scale."
    ),
    idea_prompt=(
        "Find unmet needs and friction that a focused AI writing product "
        "could solve better than the current incumbents."
    ),
    extra_instructions=(
        "Prioritise gaps around: output quality and factual accuracy consistency, "
        "voice and tone control across a document, pricing for high-volume usage, "
        "context retention across long documents, brand voice customisation, "
        "SEO workflow integration, and plagiarism/originality concerns. "
        "Ignore generic 'AI writes worse than humans' takes — focus on specific "
        "workflow breakdowns that cause paying users to churn or work around tools."
    ),
    companies=(
        TemplateCompany("Jasper", "https://jasper.ai", "ai_tools", subreddit="JasperAI", g2_slug="jasper-ai"),
        TemplateCompany("Copy.ai", "https://copy.ai", "ai_tools", g2_slug="copy-ai"),
        TemplateCompany("Writesonic", "https://writesonic.com", "ai_tools", g2_slug="writesonic"),
        TemplateCompany("Rytr", "https://rytr.me", "ai_tools", g2_slug="rytr"),
        TemplateCompany("Notion AI", "https://notion.so", "productivity", subreddit="Notion", g2_slug="notion"),
        TemplateCompany("Sudowrite", "https://sudowrite.com", "ai_tools"),
        TemplateCompany("Lex", "https://lex.page", "ai_tools"),
        TemplateCompany("Hypotenuse AI", "https://hypotenuse.ai", "ai_tools", g2_slug="hypotenuse-ai"),
    ),
    market_sources=(
        _reddit("writing", "r/writing — writer pain and tool discussion"),
        _reddit("contentcreators", "r/contentcreators — content creator workflow pain"),
        _reddit("SEO", "r/SEO — SEO content workflow discussions"),
        _hn("AI+writing+tool", "HN — AI writing tool discussions"),
    ),
)

_LEGAL_SAAS = NicheTemplate(
    id="legal-practice-management",
    name="Legal Practice Management",
    description=(
        "Pain from law firms and solo practitioners using practice management "
        "software — Clio, MyCase, Filevine, and peers."
    ),
    target_user=(
        "Solo practitioners, small and mid-size law firm partners, "
        "and legal operations leads managing firm workflows and billing."
    ),
    idea_prompt=(
        "Identify recurring pain points in legal practice management that "
        "a focused tool could solve for small and mid-size law firms."
    ),
    extra_instructions=(
        "Prioritise gaps around: time tracking accuracy and billing workflow, "
        "trust accounting compliance and automation, document management and "
        "template reliability, client portal usability, billing integration "
        "with QuickBooks/Xero, court deadline and calendar management, "
        "and mobile app reliability for field work. "
        "The buyer is often a managing partner or office manager — not a "
        "technical user. Pain that makes them look bad to clients is high signal."
    ),
    companies=(
        TemplateCompany("Clio", "https://clio.com", "vertical_saas", g2_slug="clio"),
        TemplateCompany("MyCase", "https://mycase.com", "vertical_saas", g2_slug="mycase"),
        TemplateCompany("Filevine", "https://filevine.com", "vertical_saas", g2_slug="filevine"),
        TemplateCompany("PracticePanther", "https://practicepanther.com", "vertical_saas", g2_slug="practicepanther"),
        TemplateCompany("Smokeball", "https://smokeball.com", "vertical_saas", g2_slug="smokeball"),
        TemplateCompany("LeanLaw", "https://leanlaw.co", "vertical_saas", g2_slug="leanlaw"),
        TemplateCompany("Rocket Matter", "https://rocketmatter.com", "vertical_saas", g2_slug="rocket-matter"),
    ),
    market_sources=(
        _reddit("Lawyertalk", "r/Lawyertalk — practitioner pain"),
        _reddit("smallbusiness", "r/smallbusiness — small firm operations"),
        _hn("legal+software+law+firm", "HN — legal tech discussions"),
    ),
)

_HEALTHCARE_SAAS = NicheTemplate(
    id="healthcare-practice-management",
    name="Healthcare Practice Management",
    description=(
        "Pain from mental health practitioners and medical practices using "
        "EHR and practice management software — SimplePractice, Jane, and peers."
    ),
    target_user=(
        "Solo practitioners, group practice owners, and clinic operations managers "
        "in mental health, therapy, and outpatient medical settings."
    ),
    idea_prompt=(
        "Find workflow friction and unmet needs in healthcare practice management "
        "that a focused tool could solve for small and mid-size practices."
    ),
    extra_instructions=(
        "Prioritise gaps around: insurance billing and ERA/EOB processing, "
        "scheduling reliability and patient no-show handling, telehealth "
        "integration quality, HIPAA-compliant messaging, progress note templates "
        "and documentation burden, and patient portal usability. "
        "Mental health practitioners (therapists, psychologists) are a distinct "
        "sub-segment from medical practices — flag which segment a pain applies to. "
        "Billing pain that affects cash flow is the highest signal category."
    ),
    companies=(
        TemplateCompany("SimplePractice", "https://simplepractice.com", "vertical_saas", subreddit="SimplePractice", g2_slug="simplepractice"),
        TemplateCompany("Jane App", "https://jane.app", "vertical_saas", g2_slug="jane-app"),
        TemplateCompany("TheraNest", "https://theranest.com", "vertical_saas", g2_slug="theranest"),
        TemplateCompany("TherapyNotes", "https://therapynotes.com", "vertical_saas", g2_slug="therapynotes"),
        TemplateCompany("Healthie", "https://gethealthie.com", "vertical_saas", g2_slug="healthie"),
        TemplateCompany("Tebra", "https://tebra.com", "vertical_saas", g2_slug="tebra"),
        TemplateCompany("Kareo", "https://kareo.com", "vertical_saas", g2_slug="kareo"),
    ),
    market_sources=(
        _reddit("therapists", "r/therapists — practitioner workflow pain"),
        _reddit("psychotherapy", "r/psychotherapy — clinical pain signals"),
        _reddit("medicine", "r/medicine — general practice operations"),
        _hn("EHR+practice+management", "HN — healthcare software discussions"),
    ),
)

_SALES_ENGAGEMENT = NicheTemplate(
    id="sales-engagement-revops",
    name="Sales Engagement & Revenue Ops",
    description=(
        "Pain from sales teams and RevOps leaders using outbound tools and "
        "revenue intelligence platforms — Outreach, Salesloft, Apollo, Gong, and peers."
    ),
    target_user=(
        "SDR team leads, RevOps directors, and VP Sales at B2B companies "
        "running outbound motion or managing pipeline forecasting."
    ),
    idea_prompt=(
        "Identify recurring friction in sales engagement and revenue operations "
        "tooling that a focused product could solve better than the incumbents."
    ),
    extra_instructions=(
        "Prioritise gaps around: CRM sync reliability with Salesforce and HubSpot, "
        "AI sequence quality and deliverability rates, contact data accuracy, "
        "call intelligence transcription quality, forecast accuracy, "
        "pricing as seat count scales, and integration reliability with the "
        "broader GTM stack. "
        "Distinguish between SDR-level pain (daily workflow) and RevOps/manager "
        "pain (reporting, ops) — they have different buying authority."
    ),
    companies=(
        TemplateCompany("Outreach", "https://outreach.io", "b2b_saas", g2_slug="outreach"),
        TemplateCompany("Salesloft", "https://salesloft.com", "b2b_saas", g2_slug="salesloft"),
        TemplateCompany("Apollo", "https://apollo.io", "b2b_saas", subreddit="apolloio", g2_slug="apollo-io"),
        TemplateCompany("Gong", "https://gong.io", "b2b_saas", g2_slug="gong-io"),
        TemplateCompany("Clari", "https://clari.com", "b2b_saas", g2_slug="clari"),
        TemplateCompany("Lemlist", "https://lemlist.com", "b2b_saas", g2_slug="lemlist"),
        TemplateCompany("Reply.io", "https://reply.io", "b2b_saas", g2_slug="reply"),
        TemplateCompany("Mixmax", "https://mixmax.com", "b2b_saas", g2_slug="mixmax"),
    ),
    market_sources=(
        _reddit("sales", "r/sales — frontline sales pain"),
        _reddit("salesengineers", "r/salesengineers — technical sales pain"),
        _reddit("RevOps", "r/RevOps — revenue operations pain"),
        _hn("sales+engagement+outbound", "HN — sales tool discussions"),
    ),
)

_CUSTOMER_SUPPORT = NicheTemplate(
    id="customer-support-helpdesk",
    name="Customer Support & Helpdesk",
    description=(
        "Pain from support teams and CX leaders using helpdesk platforms — "
        "Zendesk, Intercom, Front, Help Scout, Freshdesk, and peers."
    ),
    target_user=(
        "Support team leads, CX directors, and customer success managers "
        "at B2B and B2C software companies managing inbound support volume."
    ),
    idea_prompt=(
        "Find unmet needs and recurring friction in customer support tooling "
        "that a focused product could solve better than the incumbents."
    ),
    extra_instructions=(
        "Prioritise gaps around: ticket routing and triage accuracy, "
        "AI deflection quality and false-positive rate, multi-channel inbox "
        "reliability (email + chat + social), pricing as ticket volume scales, "
        "Salesforce/HubSpot integration quality, knowledge base management, "
        "and CSAT/reporting dashboard usefulness. "
        "Distinguish between SMB support teams (small volume, all-in-one needs) "
        "and enterprise CX operations (high volume, deep workflow customisation)."
    ),
    companies=(
        TemplateCompany("Zendesk", "https://zendesk.com", "b2b_saas", g2_slug="zendesk-support-suite"),
        TemplateCompany("Intercom", "https://intercom.com", "b2b_saas", g2_slug="intercom"),
        TemplateCompany("Front", "https://front.com", "b2b_saas", g2_slug="front"),
        TemplateCompany("Help Scout", "https://helpscout.com", "b2b_saas", g2_slug="help-scout"),
        TemplateCompany("Freshdesk", "https://freshdesk.com", "b2b_saas", g2_slug="freshdesk"),
        TemplateCompany("Plain", "https://plain.com", "b2b_saas"),
        TemplateCompany("Pylon", "https://usepylon.com", "b2b_saas"),
        TemplateCompany("Crisp", "https://crisp.chat", "b2b_saas", g2_slug="crisp"),
    ),
    market_sources=(
        _reddit("CustomerService", "r/CustomerService — support team pain"),
        _reddit("CustomerSuccess", "r/CustomerSuccess — CS team workflows"),
        _hn("customer+support+helpdesk", "HN — support tooling discussions"),
    ),
)

_DATA_STACK = NicheTemplate(
    id="modern-data-stack",
    name="Modern Data Stack",
    description=(
        "Pain from data engineers and analytics engineers using the modern "
        "data stack — Snowflake, dbt, Fivetran, Airbyte, Metabase, and peers."
    ),
    target_user=(
        "Data engineering leads, analytics engineers, and heads of data "
        "at B2B software companies building and maintaining data pipelines."
    ),
    idea_prompt=(
        "Identify recurring pain and unmet needs across the modern data stack "
        "that a focused tool could solve for data and analytics teams."
    ),
    extra_instructions=(
        "Prioritise gaps around: cost predictability and query cost governance "
        "(especially Snowflake), data freshness and pipeline reliability, "
        "dbt model testing and documentation burden, reverse ETL reliability, "
        "data observability and lineage visibility, semantic layer consistency, "
        "and time-to-insight for non-technical stakeholders. "
        "The data engineer and the analytics engineer are different personas "
        "with different pain — tag which one each signal applies to. "
        "Ignore vendor marketing — focus on operational pain from practitioners."
    ),
    companies=(
        TemplateCompany("Snowflake", "https://snowflake.com", "b2b_saas", subreddit="snowflake", g2_slug="snowflake"),
        TemplateCompany("dbt Labs", "https://getdbt.com", "devtools", g2_slug="dbt"),
        TemplateCompany("Fivetran", "https://fivetran.com", "b2b_saas", g2_slug="fivetran"),
        TemplateCompany("Airbyte", "https://airbyte.com", "devtools", g2_slug="airbyte"),
        TemplateCompany("Metabase", "https://metabase.com", "b2b_saas", subreddit="metabase", g2_slug="metabase"),
        TemplateCompany("Hex", "https://hex.tech", "b2b_saas", g2_slug="hex"),
        TemplateCompany("Hightouch", "https://hightouch.com", "b2b_saas", g2_slug="hightouch"),
        TemplateCompany("Dagster", "https://dagster.io", "devtools", g2_slug="dagster"),
    ),
    market_sources=(
        _reddit("dataengineering", "r/dataengineering — data engineering pain"),
        _reddit("analytics", "r/analytics — analytics team workflows"),
        _hn("data+engineering+stack", "HN — modern data stack discussions"),
        _hn("dbt+snowflake+data", "HN — dbt and Snowflake discussions"),
    ),
)


# ── Registry ──────────────────────────────────────────────────────────────────

ALL_TEMPLATES: tuple[NicheTemplate, ...] = (
    _AI_CODING,
    _NOCODE,
    _AI_WRITING,
    _LEGAL_SAAS,
    _HEALTHCARE_SAAS,
    _SALES_ENGAGEMENT,
    _CUSTOMER_SUPPORT,
    _DATA_STACK,
)

TEMPLATES_BY_ID: dict[str, NicheTemplate] = {t.id: t for t in ALL_TEMPLATES}


def get_template(template_id: str) -> NicheTemplate | None:
    return TEMPLATES_BY_ID.get(template_id)

Core flow with project locations:

API request / scheduled worker
→ api/routes/signals.py, workers/run_daily_pipeline.py, workers/jobs.py

fetch from monitored sources
→ workers/run_daily_pipeline.py, application/ingestion/service.py, adapters/web/client.py

normalize into RawPost
→ domain/post/models.py

ingest/deduplicate/store posts
→ application/ingestion/service.py, infrastructure/db/repository.py

relevance filter
→ application/extraction/relevance_filter.py

LLM extraction into Signal
→ application/extraction/service.py, domain/signal/models.py

store signals
→ application/ports/repositories.py, infrastructure/db/repository.py

score signals
→ application/scoring/service.py, domain/score/score_formula.py

cluster signals into themes
→ application/clustering/service.py, domain/cluster/models.py

synthesize gaps/opportunities
→ application/opportunity/service.py, domain/opportunity/models.py

store clusters/opportunities
→ infrastructure/db/repository.py

API reads repositories
→ api/dependencies.py, api/routes/signals.py

UI renders gaps/findings/themes/reports/sources
→ web_client/app/(app), web_client/lib/api.ts






So I’d revise the implementation plan:

Add SourceTemplate.
Add SourceCandidate.
Add renderer with required-variable skipping.
Add code-defined default templates.
Support both market-level and competitor-level templates.
Use applicable_categories: list[str].
Add deterministic ranking/precedence.
Refactor SourceSuggestionService.
Update API route.
Update tests.

Later: validation worker.
Later: DB-backed editable templates.
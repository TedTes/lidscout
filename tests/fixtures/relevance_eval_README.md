# Relevance Eval Fixture

`relevance_eval.json` is the regression set for pre-extraction relevance
filtering.

When a real pipeline run produces a surprising filter mistake, add that post to
this fixture with the corrected label before changing rules or prompts. Prefer
real false positives and false negatives over synthetic examples; they are the
cases most likely to protect product quality.

Run:

```bash
python -m workers.evaluate_relevance_filter
```

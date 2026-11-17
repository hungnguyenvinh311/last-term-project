# Search ranking grid search

REVIEWED_OFFLINE_EVALUATION

60 queries · K=5 · grid step=0.05 · live weights unchanged.

| Mode | Trials | Tied best settings | Selected cosine/text/keyword | Validation NDCG baseline → selected | Test NDCG baseline → selected |
|---|---:|---:|---|---|---|
| image | 1 | 1 | 1.00/0.00/0.00 | 1.0000 → 1.0000 | 1.0000 → 1.0000 |
| image_text | 231 | 49 | 0.60/0.25/0.15 | 0.9631 → 1.0000 | 1.0000 → 1.0000 |
| text | 21 | 12 | 0.55/0.00/0.45 | 0.8886 → 0.9551 | 0.8649 → 1.0000 |

## Limits

- Catalogue self-images/title queries are optimistic diagnostics, not independent customer queries.
- Binary labels must include all relevant products; suggested labels are not exhaustive ground truth.
- Candidate thresholds/category voting are fixed; weights cannot recover products filtered out earlier.
- Rule parser used consistently; Gemini intent and voice transcription quality are not evaluated.
- No colour quality claim without reviewed colour evidence and colour-specific queries.

# Search ranking calibration

The grid search is an offline experiment. It never updates running application weights, embeddings or database rows. Catalogue-derived relevance suggestions are unreviewed until a person checks them. They must not be reported as real search accuracy.

## Review files

- `data/evaluation/ranking_review/index.html`: 60 queries with source images and proposed relevant product IDs.
- `data/evaluation/ranking_review/review.md`: a compact table of the same proposals.
- `data/evaluation/ranking_review/cases.json`: editable evaluation inputs and review status.
- `data/evaluation/ranking_review/catalogue_audit.json`: catalogue coverage and preparation seed.
- `data/evaluation/ranking_review/customer_queries_pending.json`: twelve realistic stress-query drafts, including colour changes, negation, budgets, ANC and new external photos. Null images/labels mean undecided, not no-answer; these are excluded from the pilot until completed, grouped, split and reviewed.

There are 20 queries per mode: text, image and image+text. Thirty queries are validation and thirty are held-out test queries. Connected groups of identical images and model names stay in one split. Existing indexed images are used only for an optimistic consistency pilot. New customer photographs and natural paraphrases are still needed for a realistic evaluation.

For each case, check the query and inspect the full catalogue. Correct `relevantArticleIDs` to include every relevant product, or `[]` if no product should match. Add `reviewNotes`; set `reviewed: true` only after that case has been checked. Do not move a product group between splits or use test rankings to revise validation weights. If query wording, labels or catalogue interpretation changes after viewing the pilot's test results, create a fresh independent test set before making a final quality claim.

The colour issue needs explicit review: the current 100-product manifest has zero colour specification fields. Some names may identify a colour; an image alone is not authoritative metadata. A record can also describe a model with multiple colour variants. Review which exact colour the indexed photograph represents before labelling colour-change queries. No automatic colour labels were fabricated.

## Experiment

Run from the application root with MySQL available:

```powershell
.\.venv-ai\Scripts\python.exe scripts/tune_search_ranking.py data/evaluation/ranking_review/cases.json --output data/evaluation/grid_reviewed_run
```

The default command refuses unreviewed cases. For explicit diagnostics only:

```powershell
.\.venv-ai\Scripts\python.exe scripts/tune_search_ranking.py data/evaluation/ranking_review/cases.json --exploratory --output data/evaluation/grid_new_pilot
```

Use a new output directory for every run; previous results are retained. `--steps 20` means a 0.05 grid step and `--k 5` evaluates the first five products. The experiment uses the same retriever, canonical text, constraints, source validation and score function as the application, with the deterministic rule parser. It does not call Gemini and does not evaluate audio transcription. It does not persist search history.

| Mode | Grid | Interpretation |
|---|---|---|
| Text | 21 combinations | Cosine and keyword weights sum to one. |
| Image | One effective combination | Only image cosine carries query evidence. Multiplying all scores by a positive constant cannot improve their ordering. |
| Image+text | 231 combinations | Image cosine, additional text cosine and keyword weights sum to one. |

For each mode, select on validation NDCG@5, then Recall@5 and MRR@5. Equivalent results prefer the setting closest to the current weights; ties are reported rather than claiming a unique optimum. Only after selecting weights are held-out test metrics calculated. Report Precision@5 with denominator five, candidate recall, Hit@1 and no-answer correctness as applicable. Binary relevance is used; the NDCG score for an empty truth set is one only if no candidates are returned.

`report.json`/`report.md` compare baseline and selected weights. `features.json` stores candidate scores and parsed criteria; `rankings.json` records returned IDs and per-query metrics. Model identity, catalogue fingerprint and input-file hash identify the experiment. Features are extracted once before the weight sweep, avoiding repeated model inference for every grid point.

Candidate recall separates retrieval/filter problems from ranking problems. If a correct product is absent from the candidate set, no choice of reranking weights can recover it. Thresholds and category voting are deliberately held fixed in this first experiment.

## Findings requiring data review

The initial pilot exposed inconsistent brand metadata: IDs 70 and 74 use `Samsung Chính hãng` and `Apple Chính hãng`, whereas query parsing produces `samsung` and `apple`. ID 79 is titled Beats Solo Buds but its source brand is `Apple Chính hãng`. These records can be excluded before ranking. Original product data were not silently rewritten. Decide and document canonical brand mapping before a final benchmark.

The parser's treatment of `không dây` as a negation was a separate implementation bug. It has been corrected and covered by a regression test; the follow-up pilot is in `data/evaluation/grid_pilot_20261104_v2`. The first pilot is retained separately. Orange is now included in explicit colour constraints and covered by a hard-filter regression test.

The user subsequently confirmed the 60 labels and corrected product 79 to Beats. Brand aliases were canonicalized and affected embeddings regenerated; see `brand_review_20261104.md`. The reviewed follow-up is `data/evaluation/grid_reviewed_20261104`: validation selects text weights 0.55 cosine / 0.45 keyword and combined weights 0.60 image / 0.25 text / 0.15 keyword. Twelve text settings and 49 combined settings tie on validation; the reported selections use the documented nearest-baseline tie-break. These are catalogue-query calibration results, not proof of external-image or colour-change quality. Existing live weights remain unchanged. More catalogue items can introduce more confusing candidates, but catalogue size alone does not determine accuracy. Relevance labels, colour/brand evidence, candidate recall and encoder suitability must be evaluated together.

Follow-up: the user approved applying the selected policy and adding colour evidence. `config/search_ranking.json` is now loaded by the application, with separate text, image and combined policies. See `applied_ranking_and_colours.md` for the current configuration, 87 visual colour observations, thirteen unresolved photos and the new representation scope. Earlier pilot/reviewed reports remain preserved as historical experiments on their recorded catalogue fingerprints.

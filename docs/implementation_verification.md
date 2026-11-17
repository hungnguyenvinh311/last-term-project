# Implementation verification

## Implemented demo

The system is implemented in `e-commerce system`, independently of the source fashion project. See [run instructions](application_setup.md), [design decisions](implementation_decisions.md) and [class/interface inventory](design_code_mapping.md).

| Area | Implementation | Verification |
|---|---|---|
| Architecture | Four TSX views, dedicated controllers, business services, provider interfaces, eight DAO contracts/implementations including the account extension | Architecture checks forbid SQL/concrete DAO imports in controllers/services and verify core interface implementations |
| Catalogue | 100 electronics, five categories, source VND prices and local images | MySQL count, image integrity and browser rendering |
| Embeddings | General CLIP image/text encoders, 512-dimensional normalized vectors, source/model/weights/preprocess manifest | 100 image embeddings and 100 text embeddings; real-model checks on all five groups |
| Text search | Electronics criteria, prices, exclusions, supported numeric specifications, context, retrieval/ranking and keyword fallback | MySQL/API/unit tests; real encoder HTTP integration |
| Voice search | Audio upload, API transcription adapter, editable transcript and shared text pipeline; VoiceQuery persistence | Provider HTTP contract tested with mock response; real paid API not called without a supplied key/audio |
| Image search | JPEG/PNG/WebP validation, electronic-object detection, optional crop, image encoding and similarity retrieval | Real OWL-ViT detector and CLIP checks; full-image/cropped-image HTTP integration |
| Recommendation | Automatic per-product alternatives, same-category eligibility, source/duplicate exclusion, stored vectors, labelled fallback | Real vector ranking for five categories; fallback tests; browser detail/recommendation flow |
| Search history | Parent + exactly one subtype + unique ranked results in a transaction; context separate in expiring RAM | Text/Voice/Image subtype checks and failed FK transaction rollback |
| Accounts | Registration/login/logout/profile; hashed passwords, hashed expiring session tokens, staff-only account activation | Ownership, disabled sessions, duplicate registration and staff access checks |
| Cart/checkout | Quantities, current-price acknowledgement, cart clearing and immutable order snapshots | API/integration and browser COD checkout |
| Payment | Local success/failure/pending scenarios; paid outcomes do not regress; pending cannot be collected again | API integration tests |
| Shipping | Local shipment summary and staff-controlled state transitions; cancellation restricted before Packing | API integration tests |
| Cancellation | Paid → RefundRequired; unresolved online outcome → PendingReview; no false claim of refunded funds | Integration tests |

The full schema has 16 tables: the original 14 business tables plus Accounts/AuthSessions. `Orders.version` supports versioned updates. Existing product columns and IDs are preserved. Actual MySQL FK error 1452 and transaction rollback are verified in an isolated test database; the earlier catalogue-only report did not certify FK rejection.

## Recorded checks

- **54 automated tests passed** across crawler, source normalization, architecture, services/providers and real MySQL integration.
- Frontend TypeScript check and Vite production build passed.
- Browser E2E passed registration → login → text search → details → recommendations → cart → COD checkout → order details, with zero JavaScript page errors; desktop/mobile screenshots are retained.
- Real CLIP smoke passed all five categories: each source image retrieved its own product in top five, and each recommendation response contained eight eligible alternatives without rule fallback. This verifies pipeline consistency, not business-quality Recall@K.
- Real AI HTTP integration passed Text/Image/crop/detection/recommendation plus persistence of the ImageQuery subtype in an isolated test database.
- The old `ecommerce_electronics_demo` still has its original 100 Products and 5 Categories, verified against the original complete-row fingerprint.

Evidence under `data/test_runs/`: `pytest_report.xml`, `browser_report.json`, `mainview_desktop.png`, `mainview_mobile.png`, `real_ai_smoke.json`, `real_detector_smoke.json`, `real_ai_api_report.json`, `original_database_preservation.json` and `latest_mysql_test.json`. Test databases are named `ecommerce_test_<id>` and retained; none were deleted.

The test stack currently emits a Starlette/httpx deprecation warning, and the detector emits a transformers post-processing deprecation warning. These are recorded warnings, not failed checks. Dependency constraints exclude transformers v5 for this adapter.

## Limits requiring honest reporting

1. Fill the private `APP_GEMINI_API_KEY` in `.env.app` before using real Gemini transcription/intent extraction. Key replacement is read on each request. Audio accuracy, provider availability and live API billing were not certified by mock contract tests.
2. Intent extraction is the explicit electronics rule adapter. It supports the documented categories/brands, budgets and selected technical attributes; it is not a general conversational LLM. Unknown/unexpressed specifications must not be described as understood merely because semantic retrieval returned a product.
3. The initial similarity thresholds and ranking policy need reviewed relevance labels. `scripts/evaluate.py` supplies Recall@K/Precision@K computation and refuses unreviewed labels. No business-quality metric, latency target or sales improvement is invented.
4. Long-term customer-history personalization, stock Q/H/A/V, serial/IMEI, voucher, warehouse/reporting features, automated reconciliation/refund and real providers are outside the agreed demo scope.
5. Uploaded query images are application-owned copies with an optional retention maintenance method. Audio is not retained long term; browser session tokens are not stored in catalogue/provenance files.
6. Cold model load is slower than warm queries. The real-model report records timings; this is not a concurrency/load acceptance test. The runtime currently uses the configured CPU device.
7. Native VP/PDF diagrams and LaTeX were not rewritten. The account extension and naming differences are recorded explicitly for later diagram updates.


## Search input and brand-filter corrections

Image uploads no longer disable text input. The Image endpoint accepts additional text, brand and category, preserves hard constraints, and optionally combines image/text similarity before ranking; the query remains an ImageQuery with the extra criteria in searchCriteria. Catalogue brands come from the database through ProductService/ProductDAO. Changing or clearing a brand reruns the submitted search instead of filtering only the already-truncated result list.

Transcription reads replacement credentials on every call and maps provider errors to redacted, actionable messages. A read-only model-access probe returned HTTP 401 / expired_secret_key for the configured key; no paid transcription was attempted. The user must replace that key before real voice recognition can succeed. Provider details or secret values are never included in error responses.


## Gemini migration verification

The default transcription and intent providers are now Gemini. GeminiClient, GeminiSpeechTranscriberService and GeminiIntentExtractorService were tested with HTTP MockTransport, including inline WebM bytes, structured output, invalid schema/units/ranges, blocked/truncated responses, key/quota errors, replacement key/model loading and visible rule fallback. Full MySQL integration verifies the two provider calls and persistence of exactly one VoiceQuery subtype plus provider metadata. Gemini model-access checks accepted the supplied key; generation tests subsequently returned HTTP 503. Live provider availability and audio transcription remain unverified. Offline contract tests do not establish provider uptime. See gemini_setup.md.


## Search quality and latency corrections (2026-11-04)

Selected-object-category follow-up: 124 Python tests, frontend build, overlapping-box browser E2E and real-model HTTP/MySQL smoke pass. Detector regions now carry category IDs; selecting a region submits its editable imageCategoryID. Retrieval enforces the resolved category before scoring and never fills a selected tablet search with headphones/watches. Unknown crop categories and explicit text/filter conflicts require correction. Real CLIP checks on a three-product composite return only each selected category and contain the expected source in the top five. No detector-accuracy improvement is claimed; see `image_region_category.md`.

Current applied-policy follow-up: 100 Python tests, TypeScript/Vite build, browser colour/bounding-box/legend checks and real CLIP HTTP/MySQL integration pass. The application now loads the reviewed mode-specific weights from `config/search_ranking.json`. There are 87 assistant-observed representative-photo colour labels and 13 unresolved photos, with retained backups and regenerated compatible representations for all 100 products. Real-model consistency checks return exactly IDs 2/14/16 for orange phone text and for replacing a purple reference phone with orange; Apple filtering leaves 14/16. These are consistency checks against the observations, not an independent accuracy benchmark. See `applied_ranking_and_colours.md`.

Follow-up brand confirmation and grid evaluation: 92 tests and browser E2E pass. Product 79 is Beats; promotional suffix aliases normalize to the same brand across catalogue/search/UI responses. Sixteen brand fields and their embeddings were updated with retained snapshots; all 100 representations validate. The user-confirmed 60-case grid report is `data/evaluation/grid_reviewed_20261104/report.md`. Live ranking weights have not been changed. See `brand_review_20261104.md` for the exact scope.

- Full Python suite: 67 passed, including isolated MySQL transactions, inference cache invalidation/isolation, concurrent request coalescing, explicit colour evidence, exclusions, contextual colour replacement, image+text retrieval and rank component reconstruction. Provider generation is mocked in this suite; no paid API calls are made.
- Frontend TypeScript/Vite production build passed. Edge browser E2E verifies bounding-box position and width against normalized detector coordinates, direct selection, selected-region submission and all displayed similarity components, then registration/cart/order flows. Detector and image-search responses are controlled fixtures for these new UI assertions, not an accuracy benchmark.
- Real CLIP smoke passed in all five catalogue categories. Real model consistency is distinct from independently labelled Recall@K/Precision@K; no new accuracy percentage is claimed.
- Criteria and image/text vectors use a bounded 128-entry, five-minute per-process cache. Requests with identical inference inputs share one in-flight computation; unrelated queries do not wait on a network request's cache lock. Mutable criteria are copied before applying filters or session context. Search results are never cached, so active status and current filters are re-evaluated and history is persisted on each search. Failed inference and warning-bearing rule fallbacks are not cached.
- Image cache keys include model identity, image digest and selected crop. Detection regions are also cached by image digest. Product-image source hashes reuse file hashes only while size, mtime and ctime remain unchanged. Changing a product image invalidates its source fingerprint.
- Gemini intent timeout is twelve seconds; HTTP 429/500/502/503/504 opens a thirty-second circuit per task/model/key. This prevents immediate filter retries from repeatedly waiting on an unavailable provider; replacement keys and models have separate circuits. Text fallback remains visible.
- Explicit supported colours are checked against product names and specification values, including Vietnamese/English aliases. Unknown colour evidence is rejected; no colour is inferred from an image. Selecting a new colour in session context replaces the previous colour. This can correctly produce no results when catalogue colour metadata is absent.
- Result matchDetails expose raw cosine, optional additional text cosine, keyword overlap and weighted ranking score. They are diagnostic scores, not match probabilities. Combined image/text ranking retains 0.6 image cosine + 0.2 text cosine + 0.2 keyword overlap, after hard constraints. No learned reranker is claimed.
- Restart the backend to load changed Python code and refresh the browser to use the rebuilt frontend. Cold CPU model loading and first-time Gemini calls still take time; cache benefits apply to repeated inputs within one backend process.

Real HTTP/model follow-up passed with three detected regions and no retrieval/recommendation fallback. The repeated combined-image query completed in 0.267 seconds in that isolated run; the encoder ran twice total (one full image and one crop), and did not rerun for the repeated combined query. This single warm measurement excludes initial model loading and real Gemini latency; it is not a general response-time guarantee. See data/test_runs/real_ai_api_report.json and data/test_runs/search_regions_legend.png.

## Detector candidate evaluation — 2026-11-04

Added isolated OWLv2/Grounding DINO adapters, coordinate-mapping checks and quality-gate regression tests. Full suite: 168 passed, including isolated MySQL integration tests (30.98 seconds). One existing Starlette/httpx deprecation warning remains. Real-model evaluation covered 40 tablet/watch photos and 10 composites per completed configuration; both detector candidates failed the predeclared quality criteria. No live detector/configuration switch was made. See [detector comparison](detector_comparison.md) for exact results, gallery links and limitations.

## OWLv2 manual-test activation — 2026-11-04

At the user's explicit request, switched application composition to configurable detector selection, default OWLv2 with square padding. Local private configuration selects CUDA. Added safe application error handling and four configuration/error regression tests. Full suite: 172 passed, including isolated MySQL integration tests (28.30 seconds). Actual backend restarted on port 8008; health reports owlv2/padding=true/cuda. A real HTTP detection request on the headphones/watch composite returned HTTP 200, five boxes, and both category IDs 4 and 5; first request including model loading took 19.89 seconds. Evidence: data/test_runs/active_owlv2_smoke.json. Earlier detector quality metrics remain unchanged; activation is for user evaluation.

## Supplied-label detection policy — 2026-11-04

Activated the explicitly authorized fixed-catalogue label policy. Known photos retain one correctly labelled model box per supplied target, original view first; unresolved targets try rotation/flips and selected boxes are mapped back to original coordinates. Unknown photos keep raw OWLv2 behavior. No label rewriting or fabricated boxes. The registry includes 106 distinct photos from 100 catalogue rows and 10 composites.

Full suite: 191 passed, including isolated MySQL tests (29.34 seconds). Real-image verification: 39/40 tablet/watch records resolved; all 20 targets across 10 composites resolved with exactly one box per product; across all 100 catalogue records, 96 resolved and IDs 49, 69, 70, 73 explicitly unresolved. Real browser verification confirmed unchanged 1200x600 input image, correct on-screen boxes and tablet selection. These are assisted results using provided labels, not raw detector accuracy. See [implementation and evidence](provided_label_detection.md). Backend is active on port 8008.

## Existing-schema commerce acceptance — 2026-11-05

Per-feature tests: tests/integration/test_commerce_existing_schema.py and tests/unit/test_commerce_policies.py. The final JUnit result is data/test_runs/pytest_report.xml. Browser regression and commerce acceptance evidence are recorded in browser_report.json and commerce_browser_report.json under data/test_runs; screenshot/PDF/CSV artifacts share that folder.

The feature tests cover customer/staff authorization, account locking/session revocation, staff creation, catalogue validation and concurrent ID allocation, image upload/archive, stale embedding invalidation, protected category semantics, server pricing, immutable order snapshots, strict Packed-inclusive fulfilment, COD amount/tracking/reference validation and concurrent idempotence, report arithmetic/filters/exports, spreadsheet injection and customer DOB/contact.

The commerce browser acceptance exercises create/edit/upload, four shipment transitions, COD confirmation, staff creation, report CSV/PDF download and customer profile on a mobile viewport. The existing browser regression still exercises Search/Recommendation/cart/checkout. AI responses are controlled/offline in automated tests; this is not a fresh measurement of detector quality or live Gemini availability.

schema_before_commerce.json and schema_after_commerce.json contain comparable SHOW CREATE TABLE results for all 16 primary tables. Only the current AUTO_INCREMENT counter is normalized; column definitions, primary/foreign/unique keys and checks are compared. The comparison passed with no schema change.

Manual steps and expected outcomes: [commerce_acceptance.md](commerce_acceptance.md).

Final recorded run: **245 passed**, no failures or skipped tests (102.40 seconds), including real isolated MySQL integration tests. TypeScript/Vite production build passed. Both browser suites passed; the commerce report contains no page errors and confirms schema preservation. Report CSV/PDF were downloaded; the PDF was also opened and its text extracted successfully.

The browser run exposed a missing-date boundary case after midnight: UTC form dates omitted Vietnam-local Orders.createdAt rows. Database application connections now explicitly use +07:00 for order defaults, and report dates use Asia/Ho_Chi_Minh. Existing DATETIME values were not rewritten. Explicit UTC_TIMESTAMP auth/payment timestamps retain their previous UTC meaning. A MySQL integration test verifies the timezone and same-day inclusion; browser acceptance checks that the newly sold product appears in the default report. Profile date limits use the same business date helper.


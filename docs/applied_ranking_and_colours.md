# Applied search weights and representative-photo colours

## Active ranking policy

`config/search_ranking.json` contains the selected catalogue-calibration policy. `bootstrap.py` loads and validates it when creating the application; `SoftReranker` selects by the explicit `searchMode` returned by `CandidateRetriever`.

| Mode | Main cosine | Additional text cosine | Keyword overlap |
|---|---:|---:|---:|
| Text | 0.55 | 0 | 0.45 |
| Image | 1.00 | 0 | 0 |
| Image + text | 0.60 | 0.25 | 0.15 |

The `matchDetails.weights` response field records the actual weights used for each result. Hard brand, category, budget, colour and technical constraints are applied before ranking. Pure image search has no keyword contribution. Recommendation ranking is unchanged. Invalid configuration fails startup instead of silently accepting negative, nonfinite or non-normalized weights.

These weights were selected with the reviewed catalogue query set, not independent external photographs. Adding colour metadata changes product text embeddings; the earlier calibration report remains a historical experiment, not a fresh accuracy result for the updated representations. The active policy is provisional until the independent customer queries are completed.

## Colour scope and provenance

The assistant visually inspected contact sheets of all 100 indexed photographs. Observed primary physical colours are stored in the existing `technicalSpecs` JSON field under `Màu ảnh đại diện`; no new database table was introduced. There are 87 observed labels and 13 unresolved photos. `data/retailer_catalog/color_annotations.json` records image SHA-256, scope, method and review status for every product.

These are assistant visual observations, **not user-confirmed colour ground truth**. For phones/tablets/laptops the label refers to the visible physical body; for earphones, the main earpieces/body; for watches, the visible strap. Screen wallpapers, marketing text, packaging and printed colour-option swatches are not product colours. Observed colours do not claim that every available retailer variant matches the indexed photo.

Ambiguous finishes and photos without enough body visibility receive no hard colour label. Pending IDs are 4, 6, 19, 23, 37, 48, 49, 52, 53, 59, 84, 95 and 103. `data/evaluation/colour_review/index.html` puts these cases first and also shows the 87 observations for correction. Product images or variant assignments changing later require visual revalidation of the associated annotation.

Before updating the retailer database and product manifest, previous products, complete database rows and the embedding manifest were saved in `data/retailer_catalog/color_backup_20261104T040134661160Z`. Raw source provenance and historical catalogue data remain unchanged. No product IDs, images, prices or original technical specifications were removed.

## Search and representation changes

Colour matching uses explicit colour evidence in product names/colour specification fields, not arbitrary text such as `lên đến 256 GB`. Unknown colour is excluded from a mandatory colour query. Colour conditions remain distinct from the main embedding similarity, so the original image colour cannot override an explicit replacement colour.

`product_caption()` places the observed English colour before long technical text, within CLIP's limited context. Embeddings were regenerated for the 87 changed products; unchanged products retain compatible vectors. The frontend shows a translated `Màu ảnh` label on annotated cards, separate from the similarity legend.

The twelve customer stress-query drafts remain pending; these observations do not automatically approve their relevance labels or supply external photos.

## Verification

- Full Python suite: 100 passed, including live-policy selection, image-only ordering, invalid configuration, unknown colours, conflicting annotations and colour-caption placement; MySQL tests use isolated retained databases.
- Frontend TypeScript/Vite production build passed.
- Edge E2E checks colour label count and displayed translated colour, plus existing bounding-box/legend and commerce flows.
- Real-model HTTP consistency cases are checked by `tests/smoke/ai_api_smoke.py`: text `điện thoại màu cam` expects IDs 2, 14, 16; a purple reference photo with an orange request expects those same three IDs; adding Apple expects IDs 14 and 16. This verifies constraint enforcement and representations against the observations, not independent colour-recognition accuracy. The script writes only to the isolated test database and makes no Gemini calls.

Restart the backend after changing the weight configuration; refresh the browser after rebuilding the frontend. New external-photo queries and review of the thirteen unresolved colours are the next data-validation work.

# Detection using the supplied catalogue labels

This is the agreed closed-catalogue coursework policy. It uses explicitly supplied category labels for known photographs; it is not an improvement in unaided zero-shot detector accuracy.

## Runtime flow

1. Match the uploaded image against `data/detection_labels/manifest.json` using decoded RGB pixels and dimensions. Renaming a file or encoding identical pixels as PNG does not change the match. Resizing or changing pixels can change it.
2. Run OWLv2 + padding on the original image. For each labelled product region, retain the highest-confidence model-predicted box whose category agrees with the supplied label. Discard other boxes for that product.
3. For unresolved products, try clockwise 270°, clockwise 90°, 180°, horizontal flip, then vertical flip. Original-image selections remain fixed. Once a target is resolved, later views do not replace it. Stop when all products are resolved.
4. Invert each selected box's image transform. Padding is already removed by the underlying adapter. Return normalized coordinates on the original image, which the existing view displays and uses for cropping/search.
5. If a target is still unresolved after all views, return no box for it and report the missing category. The service does not manufacture boxes or rewrite incorrect model labels. Other products that were resolved remain available.

The threshold remains 0.15 and each underlying model pass returns at most 12 boxes. There is no NMS or voting across different views: the rule is one best correctly labelled box per supplied target, original view first. Retained scores are original model confidences, not calibrated probabilities. Metadata `sourceTransform`, `labelSource`, `targetIndex` and `articleIDs` records how each box was selected.

Unknown images retain raw OWLv2 behavior; no expected label is guessed from a filename. This policy covers the existing catalogue photos and the ten registered composite images. The manifest has 106 distinct photographs (100 catalogue rows include duplicated photos, plus ten composites). Identical catalogue photos with the same category share a target; variant article IDs remain recorded.

## Labels and configuration

Run `.venv\Scripts\python.exe scripts/prepare_detection_labels.py` to build the manifest from catalogue categories, the existing composite definitions and previously supplied coarse product regions. No predicted answers or experiment success flags are copied into the manifest. Source images, SQL tables and embeddings are untouched.

- `APP_DETECTOR_PROVIDER=owlv2`
- `APP_DETECTOR_DEVICE=cuda` on this machine; `cpu` is also supported.
- `APP_DETECTOR_LABEL_POLICY=provided_catalogue` enables this policy (default).
- `APP_DETECTOR_LABEL_POLICY=raw` restores unfiltered OWLv2 + padding. Restart the backend after changing the policy, which also clears cached detections.

`/api/health` reports `detectorLabelPolicy`. The backend is started with `.venv-ai\Scripts\python.exe -m uvicorn bootstrap:app --host 127.0.0.1 --port 8008`.

## Verification

Regression tests cover selecting a lower-scoring correct label over an incorrect high-score box, preserving original correct boxes while recovering another object, inverse coordinates on nonsquare images, stopping early, refusing wrong-panel candidates, preserving raw behavior for unknown photos, pixel-based registry matching, and reporting unresolved targets without invented labels.

Real-image verification is recorded separately by `tests/experiments/survey_single_boxes.py` and `survey_pair_boxes.py`. Their reports identify the active label policy so assisted selection is not reported as raw detector performance. Earlier raw detection surveys remain unchanged.

### Completed verification, 2026-11-04

- Full regression suite, including isolated MySQL integration: **191 passed** (29.34 seconds), one existing Starlette/httpx deprecation warning.
- [40 tablet/watch photographs](../data/detector_single_box_audit/20261104T154049Z/index.html): 19/20 tablets and 20/20 watches return exactly one correctly labelled box. Tablet #49 remains unresolved and returns an explicit missing-region message.
- [Ten composites](../data/detector_box_audit/20261104T154051Z/index.html): 20/20 targets resolved, exactly two boxes per image, no extra boxes. In `tablet__watch`, the tablet uses a clockwise-270-degree view mapped back to original coordinates, while the watch retains its original-image box.
- [All 100 catalogue records](../data/provided_catalogue_verification/20261104T154355Z/report.md): phones 20/20, laptops 20/20, tablets 19/20, headphones 17/20, watches 20/20. Total 96/100 resolved; unresolved IDs are 49, 69, 70, 73. Unresolved targets return no fabricated box or relabelled prediction.
- Real browser smoke check against the active server: the original 1200×600 composite is unchanged, both returned boxes agree with rendered screen coordinates, and selecting the recovered tablet sets category 3. Evidence: `data/test_runs/provided_labels_browser.json` and `provided_labels_browser.png`; rerun with `.venv\Scripts\python.exe tests/smoke/provided_label_detection.py`.

These are assisted results for provided labels on the fixed catalogue, not independent model accuracy or a guarantee of exact box boundaries. No frontend image rotation, product-data edits, embedding regeneration or production search-history writes were required by these detection checks.

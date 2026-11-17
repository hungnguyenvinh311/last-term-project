# Detector replacement evaluation — 2026-11-04

## Decision

Neither candidate passed the original quality gate. After reviewing the results, the user explicitly requested OWLv2 + padding for manual testing. The application now selects `Owlv2ObjectDetectorService` through `config/detector.py`; `.env.app` selects `APP_DETECTOR_PROVIDER=owlv2` and `APP_DETECTOR_DEVICE=cuda`. This manual-test activation does not change the quality results below. OWLv2 improves watches and composite images but does not solve tablet classification. Grounding DINO Tiny, under both tested query vocabularies, fails the acceptance criteria.

These are classification/localization experiments using frozen coarse product regions, not an exact bounding-box mAP evaluation. Passing software tests alone does not approve a detector.

## Implementation

Subsequently, the user authorized [supplied-label selection with rotation/flip recovery](provided_label_detection.md) for the fixed coursework catalogue. That policy is now active. The raw model comparisons below remain historical results and must not be confused with the assisted policy's verification scores.

`Model/application/ai/CandidateObjectDetectorService.py` provides OWLv2 and Grounding DINO adapters with the same `detectProducts` output contract as the existing detector: stable category ID, label, confidence and normalized coordinates. `cropRegion` is inherited. The application OWLv2 wrapper preserves safe `AIUnavailable` errors. Grounding DINO remains experimental.

The application defaults to OWLv2. CPU remains the portable example configuration; this machine's private configuration selects CUDA. Run the backend with `.venv-ai\Scripts\python.exe -m uvicorn bootstrap:app --host 127.0.0.1 --port 8008`. `/api/health` reports `detectorProvider`, `detectorPadding` and `detectorDevice`. To restore the legacy detector explicitly, set `APP_DETECTOR_PROVIDER=owlvit` and `APP_DETECTOR_MODEL=google/owlvit-base-patch32`, then restart. No silent model fallback is performed.

OWLv2 uses `google/owlv2-base-patch16-ensemble`, five original queries, threshold 0.15 and white square padding. Predicted boxes are mapped back to the original image; padding-only and degenerate boxes are discarded.

Grounding DINO uses `IDEA-Research/grounding-dino-tiny`, its own aspect-preserving processor, threshold 0.4 and no external padding. Its phrase-token scores are mapped to the same five catalogue categories. The baseline vocabulary is identical to OWL-ViT's; an additional exploratory run uses `cell phone`, `laptop`, `tablet`, `headphones`, `watch`. No product IDs, product names or ground-truth categories are inputs to inference. No per-image or per-class thresholds are applied.

On watch #81, the official Grounding DINO postprocessor returned the same incorrect `headphones` and `a mobile phone` detections as the adapter, confirming that this example is not an off-by-one class mapping error. `tests/experiments/inspect_grounding_tokens.py` reproduces the check.

## Acceptance criteria

The thresholds were recorded before the first complete run:

- Tablet strongest-region label accuracy at least 80%.
- Watch strongest-region label accuracy at least 90%.
- Each category in the paired-image benchmark at least 75% correct, with no regression against OWL-ViT plus padding.
- No inference errors; software regression tests must also pass.

The additional concise-query run is exploratory on previously observed data, not an independent holdout result. It also fails.

## Results

| Detector / configuration | Tablet, single images | Watch, single images | Correct paired targets | Accepted |
| --- | ---: | ---: | ---: | --- |
| Original OWL-ViT | 6/20 (30%) | 18/20 (90%) | 8/20 (40%) | Existing baseline |
| OWL-ViT + padding, earlier experiment | 6/20 (30%) | 18/20 (90%) | 12/20 (60%) | No |
| OWLv2 + padding | 7/20 (35%) | 19/20 (95%) | 17/20 (85%) | No |
| Grounding DINO, original queries | 2/20 (10%) | 8/20 (40%) | 2/20 (10%) | No |
| Grounding DINO, concise queries | 4/20 (20%) | 4/20 (20%) | 9/20 (45%) | No |

OWLv2 paired results: phone 4/4, laptop 4/4, tablet 1/4, headphones 4/4, watch 4/4. Its overall 85% therefore hides the unsolved tablet problem.

OWLv2 has *some* correct tablet-labelled box in 14/20 single images, but the strongest product-region box is correct in only 7/20. Availability of a correct box is not counted as correct selection.

GPU inference totals over 50 inputs, excluding model load: OWLv2 66.42 seconds; Grounding DINO original queries 42.40 seconds; concise queries 40.06 seconds. Hardware: GTX 1650 4 GB, FP32, one image at a time. These are detector timings, not end-to-end search timings. An initial CPU run was stopped after several images at roughly 16–18 seconds/image; its partial results are preserved and excluded from the completed comparison.

## Evidence

- [OWLv2 report](../data/detector_comparison/owlv2_20261104_153636/report.md) and [bounding-box gallery](../data/detector_comparison/owlv2_20261104_153636/index.html).
- [Grounding DINO original queries](../data/detector_comparison/grounding_dino_20261104_153816/report.md) and [gallery](../data/detector_comparison/grounding_dino_20261104_153816/index.html).
- [Grounding DINO concise queries](../data/detector_comparison/grounding_dino_20261104_154046/report.md) and [gallery](../data/detector_comparison/grounding_dino_20261104_154046/index.html).
- Each completed run retains `preregistered.json`, `partial_results.json`, `report.json` and all 50 annotated images. Input hashes are checked against the original benchmarks.

Run from the project root:

```powershell
.venv-ai\Scripts\python.exe tests/experiments/compare_detectors.py --kind owlv2 --device cuda
.venv-ai\Scripts\python.exe tests/experiments/compare_detectors.py --kind grounding_dino --device cuda
.venv-ai\Scripts\python.exe tests/experiments/compare_detectors.py --kind grounding_dino --device cuda --prompt-style concise
```

Each invocation creates a new result directory; the adapters use already downloaded local model files. No database writes, Gemini requests or retrieval/ranking changes occur.

## Limits and next work

The 40 single-product records include only 37 unique images (17 tablet images and 20 watch images). There are only five distinct product representatives in the ten synthetic pairs. The region tests check that a box substantially belongs to the intended product/panel, not that its edges tightly match the object. Duplicate images and repeated representatives must not be treated as independent proof of generalization.

The next substantive approach is a detector trained or fine-tuned for the five electronics categories, using manually verified object boxes, additional photos and a split by product/model. Single and composite variants of the same source product must remain in the same split. Current images can seed annotation, but are insufficient to claim general accuracy. Keep manual category correction available while the detector remains imperfect.

Primary model documentation: [OWLv2 checkpoint](https://huggingface.co/google/owlv2-base-patch16-ensemble), [Grounding DINO Tiny checkpoint](https://huggingface.co/IDEA-Research/grounding-dino-tiny).

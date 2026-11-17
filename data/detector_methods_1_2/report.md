# Fixed detector-method comparison

| Input | Condition | Tablet correct top1 | Watch correct top1 |
|---|---|---:|---:|
| singleImages | baseline | 6/20 (30.0%) | 18/20 (90.0%) |
| singleImages | padding | 6/20 (30.0%) | 18/20 (90.0%) |
| singleImages | prompts | 6/20 (30.0%) | 17/20 (85.0%) |
| singleImages | combined | 6/20 (30.0%) | 17/20 (85.0%) |
| pairedImages | baseline | 0/4 (0.0%) | 0/4 (0.0%) |
| pairedImages | padding | 0/4 (0.0%) | 4/4 (100.0%) |
| pairedImages | prompts | 0/4 (0.0%) | 0/4 (0.0%) |
| pairedImages | combined | 0/4 (0.0%) | 4/4 (100.0%) |

- Correct means highest-confidence product-region box has the expected category under the previously frozen coarse-ROI rule, not object-box IoU/mAP.
- All 40 single source photos are square; padding alone should not change them. Tablet duplicates are also reported separately.
- Paired benchmark has one catalogue representative per class, only four tablet and four watch targets.
- Prompts are a fixed balanced three-per-class bank; max-scoring prompt maps to its category. No result-driven edits or class-specific threshold tuning.
- Same development catalogue and previously observed images; no independent generalization claim.
- Prompt scores are uncalibrated confidences, not correctness probabilities. Correct-label availability is reported separately from top1.
- The baseline single-image detections are reused only after checking unchanged adapter source hash, model, prompts, threshold and source image SHA.
- No Gemini calls, new models, database writes or live detector configuration changes.

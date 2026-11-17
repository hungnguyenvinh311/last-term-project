# Detector comparison

Model: `google/owlv2-base-patch16-ensemble`. Quality gate passed: **False**.

| Group | Category | Correct | Previous baseline | Any correct | Missed |
|---|---|---:|---:|---:|---:|
| singles | 3 | 7/20 | 6/20 | 14 | 0 |
| singles | 5 | 19/20 | 18/20 | 19 | 0 |
| pairs | 1 | 4/4 | 4/4 | 4 | 0 |
| pairs | 2 | 4/4 | 4/4 | 4 | 0 |
| pairs | 3 | 1/4 | 0/4 | 3 | 0 |
| pairs | 4 | 4/4 | 0/4 | 4 | 0 |
| pairs | 5 | 4/4 | 4/4 | 4 | 0 |

- Product-region label correctness, not precise bounding-box IoU/mAP.
- Previously observed development catalogue; 40 products include only 37 unique photos.
- Pairs reuse one representative per category, not four independent products.
- Different model confidence scales; fixed thresholds, no tuning on benchmark answers.
- Grounding DINO uses phrase-token max confidence with threshold .4; processor preserves aspect ratio.
- Only inference adapters change; no changes to retrieval or Gemini calls.
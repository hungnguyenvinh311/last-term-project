# Tablet/watch screen-confusion audit

| Group | Products | Phone top1 original | Phone top1 grayscale | Any phone box original | Correct top1 original | Missed original |
|---|---:|---:|---:|---:|---:|---:|
| all40 | 40 | 12 (30.0%) | 13 (32.5%) | 15 | 24 | 0 |
| tablets | 20 | 10 (50.0%) | 11 (55.0%) | 12 | 6 | 0 |
| watches | 20 | 2 (10.0%) | 2 (10.0%) | 3 | 18 | 0 |
| rectangularWatches | 9 | 2 (22.2%) | 2 (22.2%) | 3 | 7 | 0 |
| roundWatches | 11 | 0 (0.0%) | 0 (0.0%) | 0 | 11 | 0 |
| rectangularColourful | 27 | 12 (44.4%) | 13 (48.1%) | 15 | 11 | 0 |
| rectangularColourfulWatches | 7 | 2 (28.6%) | 2 (28.6%) | 3 | 5 | 0 |

## Method and limits

- All 40 catalogue records are included; repeated image bytes are counted separately and also reported deduplicated.
- Shapes/screen appearance/coarse ROIs are assistant visual observations, not manufacturer ground truth or precise object boxes.
- Phone top1 means the highest-confidence retained product-region box is phone. Any-phone-box rate is a different, separately reported measure.
- Boxes outside the coarse ROI or below 5% ROI area are excluded only from the product assessment, not deleted from raw predictions.
- Grayscale is an input ablation on the same image, not a production fix. Differences do not isolate screen colour from every other coloured region.
- Original images retain advertising, accessories and scene layout. Association with shape/colour does not prove which internal features the model uses.
- No API provider calls, catalogue/database changes, retrieval reweighting, detector prompt/threshold tuning or model downloads were requested.

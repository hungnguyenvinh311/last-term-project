# Ảnh riêng lẻ: tablet/watch với OWLv2 + padding

| Nhóm | Số ảnh | Top1 đúng | Top1 thành Phone | Có box Phone trong vùng sản phẩm | Có box Phone ở bất kỳ đâu |
|---|---:|---:|---:|---:|---:|
| tablets | 20 | 19 | 0 | 0 | 0 |

tablets — top Phone IDs: []
tablets — any product Phone IDs: []
tablets — other wrong top IDs: [49]

| watches | 20 | 20 | 0 | 0 | 0 |

watches — top Phone IDs: []
watches — any product Phone IDs: []
watches — other wrong top IDs: []

## Tất cả sản phẩm

| ID | Nhóm đúng | Tổng box | Nhãn top trong vùng | Điểm top | Có box Phone trong vùng | Có box đúng nhãn trong vùng |
|---:|---|---:|---|---:|---|---|
| 41 | Tablet | 1 | Tablet | 0.1517 | False | True |
| 42 | Tablet | 1 | Tablet | 0.4612 | False | True |
| 43 | Tablet | 1 | Tablet | 0.4393 | False | True |
| 44 | Tablet | 1 | Tablet | 0.1808 | False | True |
| 45 | Tablet | 1 | Tablet | 0.2327 | False | True |
| 46 | Tablet | 1 | Tablet | 0.3140 | False | True |
| 47 | Tablet | 1 | Tablet | 0.4713 | False | True |
| 48 | Tablet | 1 | Tablet | 0.4853 | False | True |
| 49 | Tablet | 0 | MISSED | - | False | False |
| 50 | Tablet | 1 | Tablet | 0.3810 | False | True |
| 51 | Tablet | 1 | Tablet | 0.3115 | False | True |
| 52 | Tablet | 1 | Tablet | 0.4711 | False | True |
| 53 | Tablet | 1 | Tablet | 0.5385 | False | True |
| 54 | Tablet | 1 | Tablet | 0.2327 | False | True |
| 55 | Tablet | 1 | Tablet | 0.5222 | False | True |
| 56 | Tablet | 1 | Tablet | 0.1535 | False | True |
| 57 | Tablet | 1 | Tablet | 0.3245 | False | True |
| 58 | Tablet | 1 | Tablet | 0.3951 | False | True |
| 59 | Tablet | 1 | Tablet | 0.4853 | False | True |
| 60 | Tablet | 1 | Tablet | 0.1535 | False | True |
| 81 | Watch | 1 | Watch | 0.7353 | False | True |
| 82 | Watch | 1 | Watch | 0.7123 | False | True |
| 83 | Watch | 1 | Watch | 0.7096 | False | True |
| 84 | Watch | 1 | Watch | 0.7480 | False | True |
| 86 | Watch | 1 | Watch | 0.7385 | False | True |
| 88 | Watch | 1 | Watch | 0.7042 | False | True |
| 89 | Watch | 1 | Watch | 0.7049 | False | True |
| 91 | Watch | 1 | Watch | 0.6795 | False | True |
| 92 | Watch | 1 | Watch | 0.7471 | False | True |
| 93 | Watch | 1 | Watch | 0.6849 | False | True |
| 94 | Watch | 1 | Watch | 0.7361 | False | True |
| 95 | Watch | 1 | Watch | 0.3676 | False | True |
| 97 | Watch | 1 | Watch | 0.8098 | False | True |
| 99 | Watch | 1 | Watch | 0.4538 | False | True |
| 101 | Watch | 1 | Watch | 0.4051 | False | True |
| 102 | Watch | 1 | Watch | 0.6192 | False | True |
| 103 | Watch | 1 | Watch | 0.4865 | False | True |
| 106 | Watch | 1 | Watch | 0.8177 | False | True |
| 107 | Watch | 1 | Watch | 0.7718 | False | True |
| 108 | Watch | 1 | Watch | 0.6192 | False | True |

## Giới hạn

- All 20 tablet records and 20 watch records; 37 unique source photographs because three tablet pairs duplicate photos.
- Original full source photos, not composed or manually cropped. Existing frozen coarse product ROIs used only for evaluation.
- Reports both any phone-labelled box anywhere and phone-labelled boxes in the product ROI; promotional decorations may lie outside it.
- Top1 means highest-confidence plausible box in the product ROI, not exact object-box IoU/mAP.
- Active API keeps boxes above .15, top 12, without NMS; no model, threshold, prompt or ranking modifications.
- Inference errors/fallbacks are not counted as successful no-phone detections.
- If labelPolicy=provided_catalogue, these are label-guided retained boxes with transform recovery, not raw zero-shot predictions.
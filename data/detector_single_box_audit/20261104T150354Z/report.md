# Ảnh riêng lẻ: tablet/watch với OWLv2 + padding

| Nhóm | Số ảnh | Top1 đúng | Top1 thành Phone | Có box Phone trong vùng sản phẩm | Có box Phone ở bất kỳ đâu |
|---|---:|---:|---:|---:|---:|
| tablets | 20 | 7 | 11 | 11 | 11 |

tablets — top Phone IDs: [41, 42, 43, 44, 46, 49, 50, 56, 57, 58, 60]
tablets — any product Phone IDs: [41, 42, 43, 44, 46, 49, 50, 56, 57, 58, 60]
tablets — other wrong top IDs: [47, 52]

| watches | 20 | 19 | 0 | 6 | 6 |

watches — top Phone IDs: []
watches — any product Phone IDs: [81, 95, 99, 101, 102, 106]
watches — other wrong top IDs: [95]

## Tất cả sản phẩm

| ID | Nhóm đúng | Tổng box | Nhãn top trong vùng | Điểm top | Có box Phone trong vùng | Có box đúng nhãn trong vùng |
|---:|---|---:|---|---:|---|---|
| 41 | Tablet | 3 | Phone | 0.3320 | True | True |
| 42 | Tablet | 1 | Phone | 0.4994 | True | False |
| 43 | Tablet | 1 | Phone | 0.4777 | True | False |
| 44 | Tablet | 3 | Phone | 0.4603 | True | True |
| 45 | Tablet | 1 | Tablet | 0.2327 | False | True |
| 46 | Tablet | 2 | Phone | 0.3145 | True | True |
| 47 | Tablet | 2 | Laptop | 0.5259 | False | True |
| 48 | Tablet | 2 | Tablet | 0.4853 | False | True |
| 49 | Tablet | 1 | Phone | 0.7670 | True | False |
| 50 | Tablet | 1 | Phone | 0.3104 | True | False |
| 51 | Tablet | 2 | Tablet | 0.3115 | False | True |
| 52 | Tablet | 2 | Laptop | 0.5051 | False | True |
| 53 | Tablet | 2 | Tablet | 0.5385 | False | True |
| 54 | Tablet | 1 | Tablet | 0.2327 | False | True |
| 55 | Tablet | 3 | Tablet | 0.5222 | False | True |
| 56 | Tablet | 2 | Phone | 0.3485 | True | True |
| 57 | Tablet | 1 | Phone | 0.5384 | True | False |
| 58 | Tablet | 1 | Phone | 0.4435 | True | False |
| 59 | Tablet | 2 | Tablet | 0.4853 | False | True |
| 60 | Tablet | 2 | Phone | 0.3485 | True | True |
| 81 | Watch | 2 | Watch | 0.7353 | True | True |
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
| 95 | Watch | 2 | Headphones | 0.3760 | True | False |
| 97 | Watch | 2 | Watch | 0.8098 | False | True |
| 99 | Watch | 2 | Watch | 0.4538 | True | True |
| 101 | Watch | 2 | Watch | 0.4051 | True | True |
| 102 | Watch | 2 | Watch | 0.6192 | True | True |
| 103 | Watch | 2 | Watch | 0.4865 | False | True |
| 106 | Watch | 2 | Watch | 0.8177 | True | True |
| 107 | Watch | 1 | Watch | 0.7718 | False | True |
| 108 | Watch | 2 | Watch | 0.6192 | False | True |

## Giới hạn

- All 20 tablet records and 20 watch records; 37 unique source photographs because three tablet pairs duplicate photos.
- Original full source photos, not composed or manually cropped. Existing frozen coarse product ROIs used only for evaluation.
- Reports both any phone-labelled box anywhere and phone-labelled boxes in the product ROI; promotional decorations may lie outside it.
- Top1 means highest-confidence plausible box in the product ROI, not exact object-box IoU/mAP.
- Active API keeps boxes above .15, top 12, without NMS; no model, threshold, prompt or ranking modifications.
- Inference errors/fallbacks are not counted as successful no-phone detections.
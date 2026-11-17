# Khảo sát xoay/lật: 7 ảnh không có box đúng nhãn

Mỗi ô: Có/Không có box đúng nhãn; nếu có, kèm điểm cao nhất của box đúng.

| ID | Sản phẩm | Gốc | Xoay 90° | Xoay 180° | Xoay 270° | Lật ngang | Lật dọc |
|---:|---|---|---|---|---|---|---|
| 42 | Xiaomi Poco Pad X1 8GB 512GB | Không | Có (0.3819) | Không | Có (0.4612) | Không | Không |
| 43 | Xiaomi Pad 8 Pro 8GB 128GB | Không | Không | Không | Có (0.4393) | Không | Không |
| 49 | iPad mini 7 2024 Wifi 128GB / Chính hãng Apple Việt Nam | Không | Không | Không | Không | Không | Không |
| 50 | Lenovo Legion Tab Gen 5 12GB 256GB | Không | Có (0.2792) | Không | Có (0.3810) | Không | Không |
| 57 | iPad Pro chip M5 11 inch Wifi 256GB / Chính hãng Apple Việt Nam | Không | Không | Không | Có (0.3245) | Không | Không |
| 58 | Xiaomi Redmi Pad 2 9.7 inch Wifi 4GB 64GB | Không | Không | Không | Có (0.3951) | Không | Không |
| 95 | Apple Watch SE 3 GPS 40mm Viền nhôm dây cao su | Không | Có (0.2226) | Không | Có (0.3676) | Không | Có (0.3179) |

## Tổng hợp

Có ít nhất một biến đổi thành công: [42, 43, 50, 57, 58, 95]
Vẫn không có box đúng ở mọi phiên bản: [49]
Lỗi thực thi: 0

- Gốc: có box đúng 0/7; box cao điểm nhất đúng 0/7.
- Xoay 90°: có box đúng 3/7; box cao điểm nhất đúng 2/7.
- Xoay 180°: có box đúng 0/7; box cao điểm nhất đúng 0/7.
- Xoay 270°: có box đúng 6/7; box cao điểm nhất đúng 6/7.
- Lật ngang: có box đúng 0/7; box cao điểm nhất đúng 0/7.
- Lật dọc: có box đúng 1/7; box cao điểm nhất đúng 0/7.

## Giới hạn

- Seven previously failed development images, not a random or held-out sample.
- Six fixed views: unchanged decoded pixels, clockwise 90/180/270 degrees, horizontal and vertical reflection. PNG encoding avoids additional JPEG loss.
- Product ROI is transformed together with the image and used only for assessment, never provided to the detector.
- Success means at least one returned correctly labelled box in the product ROI, not exact object IoU/mAP or a correct highest-score box.
- Threshold .15 and top 12 are unchanged; no NMS, per-image prompt changes or production transform aggregation.
- Increased success after trying several views is measured on selected failures and does not establish overall accuracy.
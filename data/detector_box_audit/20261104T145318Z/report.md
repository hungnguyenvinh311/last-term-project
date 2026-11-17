# Khảo sát bounding box OWLv2 + padding

| Ảnh ghép | Tổng box | Sản phẩm trái: số box và box điểm cao nhất | Sản phẩm phải: số box và box điểm cao nhất | Box ngoài hai vùng |
|---|---:|---|---|---:|
| phone__laptop | 5 | Phone: 3 box; #2 Phone 0.3868; Đúng | Laptop: 2 box; #1 Laptop 0.5601; Đúng | 0 |
| phone__tablet | 6 | Phone: 3 box; #1 Phone 0.5280; Đúng | Tablet: 3 box; #2 Phone 0.4423; Sai | 0 |
| phone__headphones | 7 | Phone: 3 box; #1 Phone 0.4898; Đúng | Headphones: 4 box; #3 Headphones 0.2557; Đúng | 0 |
| phone__watch | 4 | Phone: 3 box; #2 Phone 0.4356; Đúng | Watch: 1 box; #1 Watch 0.7029; Đúng | 0 |
| laptop__tablet | 5 | Laptop: 2 box; #1 Laptop 0.5473; Đúng | Tablet: 3 box; #2 Tablet 0.4124; Đúng | 0 |
| laptop__headphones | 9 | Laptop: 2 box; #1 Laptop 0.5990; Đúng | Headphones: 7 box; #2 Headphones 0.3227; Đúng | 0 |
| laptop__watch | 4 | Laptop: 2 box; #2 Laptop 0.5952; Đúng | Watch: 2 box; #1 Watch 0.7214; Đúng | 0 |
| tablet__headphones | 8 | Tablet: 3 box; #1 Phone 0.3449; Sai | Headphones: 5 box; #4 Headphones 0.2536; Đúng | 0 |
| tablet__watch | 4 | Tablet: 3 box; #2 Phone 0.3129; Sai | Watch: 1 box; #1 Watch 0.7074; Đúng | 0 |
| headphones__watch | 5 | Headphones: 4 box; #2 Headphones 0.2592; Đúng | Watch: 1 box; #1 Watch 0.7406; Đúng | 0 |

## Tổng hợp

{
  "images": 10,
  "totalBoxes": 57,
  "targets": 20,
  "correctTopPerTarget": 17,
  "targetsWithMultipleBoxes": 17,
  "targetsWithAnyCorrectBox": 19,
  "imagesWithCorrectGlobalTop": 9,
  "unassignedBoxes": 0,
  "overlappingBoxPairsIoU50": 13
}

## Giới hạn

- Counts refer to boxes returned by the active API: confidence > 0.15 and at most 12 per image, before any NMS.
- Each expected product is identified using its panel: box center inside panel and at least 80% of box area inside panel.
- Correct means correct category for that panel, not precise IoU against a manually labelled object box.
- Ten pairs reuse five source products; 20 target occurrences are not 20 distinct products.
- An overlapping pair with IoU >= 0.5 is a duplicate candidate, not proof: headphones may contain separate earbuds/case.
- Scores are uncalibrated detector confidence, not probabilities of being correct. No detector settings or ranking changes.
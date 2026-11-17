# Khảo sát bounding box OWLv2 + padding

| Ảnh ghép | Tổng box | Sản phẩm trái: số box và box điểm cao nhất | Sản phẩm phải: số box và box điểm cao nhất | Box ngoài hai vùng |
|---|---:|---|---|---:|
| phone__laptop | 2 | Phone: 1 box; #1 Phone 0.3868; Đúng | Laptop: 1 box; #2 Laptop 0.5601; Đúng | 0 |
| phone__tablet | 2 | Phone: 1 box; #1 Phone 0.5280; Đúng | Tablet: 1 box; #2 Tablet 0.2271; Đúng | 0 |
| phone__headphones | 2 | Phone: 1 box; #1 Phone 0.4898; Đúng | Headphones: 1 box; #2 Headphones 0.2557; Đúng | 0 |
| phone__watch | 2 | Phone: 1 box; #1 Phone 0.4356; Đúng | Watch: 1 box; #2 Watch 0.7029; Đúng | 0 |
| laptop__tablet | 2 | Laptop: 1 box; #1 Laptop 0.5473; Đúng | Tablet: 1 box; #2 Tablet 0.4124; Đúng | 0 |
| laptop__headphones | 2 | Laptop: 1 box; #1 Laptop 0.5990; Đúng | Headphones: 1 box; #2 Headphones 0.3227; Đúng | 0 |
| laptop__watch | 2 | Laptop: 1 box; #1 Laptop 0.5952; Đúng | Watch: 1 box; #2 Watch 0.7214; Đúng | 0 |
| tablet__headphones | 2 | Tablet: 1 box; #1 Tablet 0.3315; Đúng | Headphones: 1 box; #2 Headphones 0.2536; Đúng | 0 |
| tablet__watch | 2 | Tablet: 1 box; #1 Tablet 0.5011; Đúng | Watch: 1 box; #2 Watch 0.7074; Đúng | 0 |
| headphones__watch | 2 | Headphones: 1 box; #1 Headphones 0.2592; Đúng | Watch: 1 box; #2 Watch 0.7406; Đúng | 0 |

## Tổng hợp

{
  "images": 10,
  "totalBoxes": 20,
  "targets": 20,
  "correctTopPerTarget": 20,
  "targetsWithMultipleBoxes": 0,
  "targetsWithAnyCorrectBox": 20,
  "imagesWithCorrectGlobalTop": 10,
  "unassignedBoxes": 0,
  "overlappingBoxPairsIoU50": 0
}

## Giới hạn

- Counts refer to boxes returned by the active API: confidence > 0.15 and at most 12 per image, before any NMS.
- Each expected product is identified using its panel: box center inside panel and at least 80% of box area inside panel.
- Correct means correct category for that panel, not precise IoU against a manually labelled object box.
- Ten pairs reuse five source products; 20 target occurrences are not 20 distinct products.
- An overlapping pair with IoU >= 0.5 is a duplicate candidate, not proof: headphones may contain separate earbuds/case.
- Scores are uncalibrated detector confidence, not probabilities of being correct. No detector settings or ranking changes.
- If labelPolicy=provided_catalogue, counts refer to label-guided retained boxes with transform recovery, not unfiltered detector output.
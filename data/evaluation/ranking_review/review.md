# Ranking query review

60 catalogue queries: 20 text, 20 image, 20 image + text. 60/60 labels reviewed.
30 validation and 30 held-out test queries, separated by connected model/image groups.
These catalogue-derived queries are optimistic diagnostics, not external customer-query accuracy.
Review every relevantArticleIDs list against the full catalogue, not just the suggested source. Add every genuinely relevant ID; use [] for no-answer queries.
Edit cases.json: correct text/labels, add reviewNotes and set reviewed=true only after review. Keep groupID and split consistent. Do not inspect test rankings to adjust validation weights.
Colour-critical queries and new external photos must be added before production tuning. A model-level record may not identify the exact colour pictured.

| Case | Split | Query | Proposed relevant products |
|---|---|---|---|
| text-6 | validation | điện thoại HONOR 600S 5G 6GB 128GB | 6: HONOR 600S 5G 6GB 128GB |
| image-6 | validation | (Image only) | 6: HONOR 600S 5G 6GB 128GB |
| image_text-6 | validation | điện thoại HONOR | 6: HONOR 600S 5G 6GB 128GB |
| text-5 | validation | điện thoại Samsung Galaxy A17 5G 8GB 128GB | 5: Samsung Galaxy A17 5G 8GB 128GB |
| image-5 | validation | (Image only) | 5: Samsung Galaxy A17 5G 8GB 128GB |
| image_text-5 | validation | điện thoại Samsung | 5: Samsung Galaxy A17 5G 8GB 128GB |
| text-3 | test | điện thoại Xiaomi POCO F8 Pro 5G 12GB 256GB | 3: Xiaomi POCO F8 Pro 5G 12GB 256GB |
| image-3 | test | (Image only) | 3: Xiaomi POCO F8 Pro 5G 12GB 256GB |
| image_text-3 | test | điện thoại Xiaomi | 3: Xiaomi POCO F8 Pro 5G 12GB 256GB |
| text-15 | test | điện thoại iPhone 18 Pro Max 256GB | 15: iPhone 18 Pro Max 256GB; 18: iPhone 18 Pro Max 512GB |
| image-15 | test | (Image only) | 15: iPhone 18 Pro Max 256GB; 18: iPhone 18 Pro Max 512GB |
| image_text-15 | test | điện thoại Apple | 15: iPhone 18 Pro Max 256GB; 18: iPhone 18 Pro Max 512GB |
| text-32 | validation | laptop Laptop MSI Cyborg 15 A13UC-2082VN | 32: Laptop MSI Cyborg 15 A13UC-2082VN |
| image-32 | validation | (Image only) | 32: Laptop MSI Cyborg 15 A13UC-2082VN |
| image_text-32 | validation | laptop MSI | 32: Laptop MSI Cyborg 15 A13UC-2082VN |
| text-35 | validation | laptop Laptop Lenovo IdeaPad Slim 3 14AHP10 83K9004RVN | 35: Laptop Lenovo IdeaPad Slim 3 14AHP10 83K9004RVN |
| image-35 | validation | (Image only) | 35: Laptop Lenovo IdeaPad Slim 3 14AHP10 83K9004RVN |
| image_text-35 | validation | laptop Lenovo | 35: Laptop Lenovo IdeaPad Slim 3 14AHP10 83K9004RVN |
| text-21 | test | laptop Laptop Lenovo LOQ 15IRH11E 83Y9003VVN | 21: Laptop Lenovo LOQ 15IRH11E 83Y9003VVN |
| image-21 | test | (Image only) | 21: Laptop Lenovo LOQ 15IRH11E 83Y9003VVN |
| image_text-21 | test | laptop Lenovo | 21: Laptop Lenovo LOQ 15IRH11E 83Y9003VVN |
| text-23 | test | laptop Laptop Acer Swift Air 14 SFA14-I31-55NR | 23: Laptop Acer Swift Air 14 SFA14-I31-55NR |
| image-23 | test | (Image only) | 23: Laptop Acer Swift Air 14 SFA14-I31-55NR |
| image_text-23 | test | laptop Acer | 23: Laptop Acer Swift Air 14 SFA14-I31-55NR |
| text-53 | validation | máy tính bảng Lenovo Yoga Tab Wifi 12GB 256GB TB710 ZAG60105VN - Kèm bút, bàn phím | 53: Lenovo Yoga Tab Wifi 12GB 256GB TB710 ZAG60105VN - Kèm bút, bàn phím |
| image-53 | validation | (Image only) | 53: Lenovo Yoga Tab Wifi 12GB 256GB TB710 ZAG60105VN - Kèm bút, bàn phím |
| image_text-53 | validation | máy tính bảng Lenovo | 53: Lenovo Yoga Tab Wifi 12GB 256GB TB710 ZAG60105VN - Kèm bút, bàn phím |
| text-56 | validation | máy tính bảng iPad Air 11 inch M4 Wifi 128GB 2026 / Chính hãng | 56: iPad Air 11 inch M4 Wifi 128GB 2026 / Chính hãng; 60: iPad Air 11 inch M4 Wifi 256GB 2026 / Chính hãng |
| image-56 | validation | (Image only) | 56: iPad Air 11 inch M4 Wifi 128GB 2026 / Chính hãng; 60: iPad Air 11 inch M4 Wifi 256GB 2026 / Chính hãng |
| image_text-56 | validation | máy tính bảng Apple | 56: iPad Air 11 inch M4 Wifi 128GB 2026 / Chính hãng; 60: iPad Air 11 inch M4 Wifi 256GB 2026 / Chính hãng |
| text-42 | test | máy tính bảng Xiaomi Poco Pad X1 8GB 512GB | 42: Xiaomi Poco Pad X1 8GB 512GB |
| image-42 | test | (Image only) | 42: Xiaomi Poco Pad X1 8GB 512GB |
| image_text-42 | test | máy tính bảng Xiaomi | 42: Xiaomi Poco Pad X1 8GB 512GB |
| text-55 | test | máy tính bảng HONOR Pad 10 Wifi 8GB 256GB | 55: HONOR Pad 10 Wifi 8GB 256GB |
| image-55 | test | (Image only) | 55: HONOR Pad 10 Wifi 8GB 256GB |
| image_text-55 | test | máy tính bảng HONOR | 55: HONOR Pad 10 Wifi 8GB 256GB |
| text-79 | validation | tai nghe Tai nghe Bluetooth True Wireless Beats Solo Buds | 79: Tai nghe Bluetooth True Wireless Beats Solo Buds |
| image-79 | validation | (Image only) | 79: Tai nghe Bluetooth True Wireless Beats Solo Buds |
| image_text-79 | validation | tai nghe Beats | 79: Tai nghe Bluetooth True Wireless Beats Solo Buds |
| text-70 | validation | tai nghe Tai nghe Samsung Galaxy Buds 4 Pro | 70: Tai nghe Samsung Galaxy Buds 4 Pro |
| image-70 | validation | (Image only) | 70: Tai nghe Samsung Galaxy Buds 4 Pro |
| image_text-70 | validation | tai nghe Samsung | 70: Tai nghe Samsung Galaxy Buds 4 Pro |
| text-66 | test | tai nghe Tai nghe Bluetooth không dây Xiaomi Buds 6 (ANC) | 66: Tai nghe Bluetooth không dây Xiaomi Buds 6 (ANC) |
| image-66 | test | (Image only) | 66: Tai nghe Bluetooth không dây Xiaomi Buds 6 (ANC) |
| image_text-66 | test | tai nghe Xiaomi | 66: Tai nghe Bluetooth không dây Xiaomi Buds 6 (ANC) |
| text-74 | test | tai nghe Tai nghe Bluetooth Apple AirPods Pro 3 2025 Type-C / Chính hãng (MFHP4ZP/A) | 74: Tai nghe Bluetooth Apple AirPods Pro 3 2025 Type-C / Chính hãng (MFHP4ZP/A) |
| image-74 | test | (Image only) | 74: Tai nghe Bluetooth Apple AirPods Pro 3 2025 Type-C / Chính hãng (MFHP4ZP/A) |
| image_text-74 | test | tai nghe Apple | 74: Tai nghe Bluetooth Apple AirPods Pro 3 2025 Type-C / Chính hãng (MFHP4ZP/A) |
| text-97 | validation | đồng hồ Huawei Watch GT 7 41mm Silicone | 97: Huawei Watch GT 7 41mm Silicone |
| image-97 | validation | (Image only) | 97: Huawei Watch GT 7 41mm Silicone |
| image_text-97 | validation | đồng hồ Huawei | 97: Huawei Watch GT 7 41mm Silicone |
| text-94 | validation | đồng hồ Đồng hồ thông minh Amazfit Balance 3 | 94: Đồng hồ thông minh Amazfit Balance 3 |
| image-94 | validation | (Image only) | 94: Đồng hồ thông minh Amazfit Balance 3 |
| image_text-94 | validation | đồng hồ Amazfit | 94: Đồng hồ thông minh Amazfit Balance 3 |
| text-107 | test | đồng hồ Honor Choice Infowear Watch 2 Pro | 107: Honor Choice Infowear Watch 2 Pro |
| image-107 | test | (Image only) | 107: Honor Choice Infowear Watch 2 Pro |
| image_text-107 | test | đồng hồ HONOR | 107: Honor Choice Infowear Watch 2 Pro |
| text-103 | test | đồng hồ Apple Watch Ultra 3 GPS + Cellular 49mm Viền titan Dây Ocean | 103: Apple Watch Ultra 3 GPS + Cellular 49mm Viền titan Dây Ocean |
| image-103 | test | (Image only) | 103: Apple Watch Ultra 3 GPS + Cellular 49mm Viền titan Dây Ocean |
| image_text-103 | test | đồng hồ Apple | 103: Apple Watch Ultra 3 GPS + Cellular 49mm Viền titan Dây Ocean |

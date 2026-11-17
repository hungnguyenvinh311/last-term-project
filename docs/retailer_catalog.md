# Vietnamese retailer catalogue — separate from historical data

The user selected a new catalogue with VND prices and correctly matched product images, in a separate database. The existing `ecommerce_electronics_demo` catalogue and its 100 historical products are preserved.

## Files and source modules

- `crawler/sources/retailers.py`: parses each public product page's Product JSON-LD; rejects category AggregateOffer prices and excludes reviews/customer information.
- `crawler/sources/retailer_sample.py`: shared public client, robots checks, two-second request spacing, no access-control bypass.
- `crawler/retailer_catalog.py`: listing discovery, collection checkpoints, stable ID mapping, product-image association, validation, gallery and explicit database import.
- `data/retailer_catalog/products.json`: normalized Product records.
- `data/retailer_catalog/provenance.json`: provider/SKU, original source URL, collection time and source price basis per articleID.
- `data/retailer_catalog/images_manifest.json`: source and local image paths, articleID, dimensions, file type and SHA-256.
- `data/retailer_catalog/product_key_map.json`: stable integer IDs for this catalogue, independent of old IDs.
- `data/retailer_catalog/checkpoint.json`: resume without repeatedly requesting completed products.
- `data/retailer_catalog/source_policy_checks.json`: source/media-host robots evidence.
- `data/retailer_catalog/validation_report.json`: measured completeness and integrity results.
- `data/retailer_catalog/index.html`: standalone searchable/filterable gallery using downloaded images.

Source pages are ordinary public product paths from CellphoneS and FPT Shop. CellphoneS supplies the main catalogue; FPT Shop supplies additional smartwatches when the main listing is insufficient. Smart bands and watch accessories are excluded. It does not call private catalogue APIs or collect user accounts/reviews. A product is accepted only if its own page supplies a positive VND price and at least one downloadable valid image. Source warranty/specifications are not fabricated. `isActive` enables a local demo record; it does not guarantee present-day stock.

## Run in PowerShell

From `e-commerce system`:

```powershell
.\.venv\Scripts\python.exe -m crawler.retailer_catalog collect --per-category 20
.\.venv\Scripts\python.exe -m crawler.retailer_catalog validate
.\.venv\Scripts\python.exe -m crawler.retailer_catalog import-mysql
Invoke-Item "data\retailer_catalog\index.html"
```

The target is **`ecommerce_vn_retailer_demo`**. Credentials are reused from `.env`, but `.env`'s original MYSQL_DATABASE is not changed. The importer refuses that original target, refuses unmanaged existing tables, and uses the same approved Categories/Products DDL. After creation, a local database manifest identifies the managed catalogue for repeat imports. Never discard this marker or the key map while reimporting.

The order of URLs can change as source listings change. Cached completed records retain their own collection timestamps; this is a resumable snapshot, not a live-price synchronization service. Exact duplicate product names are excluded. Distinct storage/configuration variants can be separate source products and retain their explicit source title/SKU; they are not silently merged.

SQL and Python store paths rather than image bytes. Each product's main image is one of its own manifest entries; additional source-declared images are retained only when available and nonduplicated. No duplicate images are manufactured to reach a count. Source image resolutions are recorded; small thumbnails can limit later image-retrieval quality. No embeddings or retrieval-model quality are claimed in this task.

## View in Workbench

Refresh SCHEMAS after import and run:

```sql
SELECT c.subCategory, COUNT(*) AS products, COUNT(p.imagePath) AS mainImages
FROM ecommerce_vn_retailer_demo.Products p
JOIN ecommerce_vn_retailer_demo.Categories c ON c.categoryID=p.categoryID
GROUP BY c.categoryID,c.subCategory;

SELECT articleID,productName,brand,price,currency,imagePath
FROM ecommerce_vn_retailer_demo.Products ORDER BY articleID;
```

Workbench shows image paths. Open the local HTML gallery to see the actual images. Retailer image copyright is retained in provenance; no CC0/open licence is asserted, and no permission for public redistribution is claimed.

## Verified results

- 100 products: 20 in each of Smartphone, Laptop, Tablet, Headphones and Smartwatch.
- All 100 have positive source VND prices and a locally downloaded main image associated through articleID and the product-page manifest.
- 100 image entries contain 96 distinct image byte hashes; some source variants share a photo. No artificial extra photos were generated.
- Two source records lack a brand and one lacks structured specifications; missing values remain null. Warranty and embeddings are not fabricated.
- MySQL `ecommerce_vn_retailer_demo`: 100 Products, 5 Categories, 100 image paths, zero orphan products.
- Repeated import preserved the complete row fingerprint. The original `ecommerce_electronics_demo` still has its original 100 Products and 5 Categories with an unchanged fingerprint.
- 15 automated tests passed, including original-database protection and image ownership validation.

Evidence: `validation_report.json`, `mysql_validation_report.json`, and `preservation_and_repeat_import_report.json` under `data/retailer_catalog/`. Image association is based on the source product page; this is not independent visual authentication of every manufacturer's photo. SQL foreign-key rejection is not certified by this report; importer category validation and measured zero-orphan checks are verified.

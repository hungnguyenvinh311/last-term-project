# Setup and measured validation

## Approved decisions

- Product uses integer `articleID` consistently. External provider/SKU identity lives in `data/normalized/product_key_map.json` and provenance manifests.
- `imagePath` is one main image. Additional media and licences live in a file manifest; no ProductImage class/table is added.
- Use real source prices, not generated prices. The user will enter MySQL credentials into the local `.env` file.

## Scope

SQL currently implements the two catalogue entities required for acquisition: Categories and Products. The other 12 existing classes are mapped in `class_diagram_db_mapping.md` but their unresolved age/session/naming differences are not silently turned into migrations. No existing diagrams or PostgreSQL application files are changed.

## Windows PowerShell

Open PowerShell in this project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The local `.env` has been created from `.env.example` without a password. Enter the correct MySQL host, port, account, password and a **new dedicated development database name** there. Do not paste credentials into chat or commands. The default database name is `ecommerce_electronics_demo`.

```powershell
.\.venv\Scripts\python.exe -m crawler.cli db-check
.\.venv\Scripts\python.exe -m crawler.cli sample
```

Review `data/sample/products.json`, `provenance.json` and `validation_report.json` before proceeding. Acquisition uses a CC0 source snapshot and preserves its original prices as historical USD figures, not current offers. Bulk acquisition must not be described as live retailer scraping.

After accepting source limitations and reviewing the sample:

```powershell
.\.venv\Scripts\python.exe -m crawler.cli collect --per-category 20
.\.venv\Scripts\python.exe -m crawler.cli validate
.\.venv\Scripts\python.exe -m crawler.cli db-init
.\.venv\Scripts\python.exe -m crawler.cli import-mysql
.\.venv\Scripts\python.exe -m crawler.cli validate-mysql
```

Initialization refuses an already populated schema. The SQL file itself uses CREATE TABLE IF NOT EXISTS; initialization never drops or alters existing tables. For a new empty database in MySQL Workbench, run `database/001_catalog.sql` once, then run the Python importer; do not run db-init after creating tables through Workbench.

## Import repeatability

The key map must be preserved between runs. Product imports use transactions, FK checks, row locks, a MySQL import lock and UPSERT. A conflicting product/category identity aborts the transaction. Reimport preserves embeddings and an existing main image when the new value is NULL. No customer/order/payment data is invented. Before changing input identity rules, back up the dedicated database and manifests.

To verify idempotence, record `validate-mysql`, run the same `import-mysql` again, and compare counts and product keys. Repeated live import passed: the count remained 100 and complete product records were unchanged. See the validation-status section for the separate FK enforcement limitation. Atomic file writes do not guarantee safety against simultaneous collection processes; run only one collection process at a time.

## Images

External `img.bbystatic.com` URLs are retained as provenance only, not automatically downloaded. The source repository's dataset licence is not treated as proof that every linked image is reusable. Products without cleared images have imagePath=NULL. `crawler/media/images.py` validates explicitly reviewed image entries (licence, creator, source URL and host policy), image format, dimensions, corruption and SHA-256 deduplication. Media acquisition is not claimed complete until such entries exist and the actual downloaded files are checked.

If an image is later cleared, its local relative path can be set as Product.imagePath and extra images recorded in images_manifest.json. Do not invent placeholder product images. Embeddings stay NULL in this stage; there is no VECTOR(n) assumption or model-quality claim.

### Retailer sample requested subsequently

Four local product images and their matching VND prices have now been collected from the public CellphoneS/FPT Shop pages selected by the user. Open `data/retailer_sample/index.html` directly in a browser to view them. This is a separate read-only pilot; it does not add images to the old Best Buy models or change MySQL. Retailer copyright is recorded without an open-licence assertion. One attempted URL returned 404. See the source assessment for the updated source scope and exact results.

## Validation status

- Normalization and repeat-collection tests: 8 passed using the already installed sibling Python environment; no package installation or sibling source changes were performed.
- MySQL connection verified: server 9.7.0. Created ecommerce_electronics_demo only after confirming the target was empty. Created Categories and Products, and imported 100 products. Other databases were not changed. Credentials were not logged.
- Source sample: 5 records, one per target category; 5/5 have name, brand, description and source price. Local images: 0/5.
- Full metadata dataset: 100 records, 20 each for Smartphone, Laptop, Tablet, Headphones and Smartwatch. Name/brand/description/price coverage is 100/100. Duplicate internal IDs and invalid category IDs: 0. See data/normalized/validation_report.json.
- Licensed local images and matching image display: not yet completed.
- Live database checks: 100 products, 20/category, zero orphan rows; repeated import retained an identical full-row fingerprint. FK declaration is present, but an invalid FK insert was unexpectedly accepted before rollback; database-side FK enforcement is NOT certified. The test transaction was rolled back and all 100 original rows remain. Importer additionally rejects unapproved category IDs before connecting. Images and embeddings remain NULL; image display is pending.

No test-count or completion claim should be inferred for unexecuted stages.

`isActive=true` means the record is enabled in this local demo catalogue; it is not a claim of present-day retailer stock. `collected_at` is the acquisition time, not the original observation time of the historical price. The source does not supply a price-observation date, so that field remains NULL in provenance.

## Useful queries

Open `database/002_example_queries.sql` in Workbench for category counts, source-currency price filtering, name search and main-image lookup. Additional image provenance is in the manifest, since the approved design has no image table.


## Separate VND retailer catalogue

The user-selected new catalogue is complete in `ecommerce_vn_retailer_demo`: 100 products, 20 per category, all with VND source prices and downloaded main images. CellphoneS is supplemented by FPT Shop for smartwatches. The original 100-product database was preserved and checked by full row fingerprint; repeat import is unchanged. See [retailer catalogue](retailer_catalog.md) for commands, measured limitations and reports. Open `data/retailer_catalog/index.html` to view images.

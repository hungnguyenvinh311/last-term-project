# Electronic product source assessment

Status: updated 2026-11-03. Acquired an official CC0 metadata snapshot, tested 5 products, then normalized 100 records. No external images downloaded and no MySQL import executed.

## Candidates checked

| Source | Primary-source evidence | Suitability / constraints |
|---|---|---|
| Wikidata | https://www.wikidata.org/wiki/Wikidata:Licensing ; https://www.wikidata.org/wiki/Wikidata:For_developers | Structured entity data is CC0. Can identify real electronic product models and source identifiers. Price, full specifications and warranty are not reliably available; actual coverage must be tested on 3–5 products before accepting it. Not a live retail inventory. |
| Wikimedia Commons | https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia/en | Potential product images. Each file has its own licence and attribution requirements. Only download an image after checking its actual file-page licence metadata. Does not imply all images share CC0 or one licence. |
| Best Buy official Products API | https://developer.bestbuy.com/apis ; https://developers.bestbuy.com/legal | Real catalogue API with product data. Requires a valid key and has restricted use terms tied to its products/applications. Not selected by default for a standalone educational catalogue. Access to a public endpoint does not settle image reuse rights. |

## Decision needed

- Option A: open factual catalogue (Wikidata + individually checked Commons images), accepting genuinely missing prices/specifications and NULL values. Good provenance; incomplete checkout data is an explicit limitation.
- Option B: choose a retail catalogue/API or a licensed dataset with permission and real prices. The specific provider/dataset and licence must be established before acquisition. Do not scrape an arbitrary retailer while its permission is unclear.

The five categories in the task (Smartphone, Laptop, Tablet, Headphones, Smartwatch) are suggestions; Category in the actual diagram specifies fields, not an existing set of category rows. A proposed target is 20 items/category initially, subject to source/category approval and measured availability.

## Checks required before acquisition

1. Check the selected endpoint's terms, robots policy where applicable, API access policy and rate limits; record exact URLs and check timestamp.
2. Fetch 3–5 real products, inspect fields and report coverage before increasing the volume.
3. For each image, retain file/source URL, creator, licence and attribution; reject unknown or incompatible rights.
4. Use a descriptive user agent, timeout, bounded retries, delay and checkpointing. No login/CAPTCHA/rate-limit bypass.
5. Persist raw responses separately from normalized data. Preserve original currencies and missing fields; do not infer current prices from release prices.
6. Report actual counts and shortfalls. Do not duplicate product variants or images merely to reach the target.

No source is yet claimed to meet the 100–150 product target. No source-specific crawl authorization/robots outcome is claimed from this preliminary licence research alone.


## Selected metadata source and executed results

The official BestBuyAPIs/open-data-set repository publishes products.json.gz and LICENSE (CC0-1.0):

- https://github.com/BestBuyAPIs/open-data-set
- https://raw.githubusercontent.com/BestBuyAPIs/open-data-set/master/LICENSE
- https://raw.githubusercontent.com/BestBuyAPIs/open-data-set/master/products.json.gz

This is not the separate BestBuy/api-playground dataset, whose README states different limitations and a different dataset licence. It is also not an authenticated production Best Buy API.

The source snapshot contains 51,646 records, acquired as a 6,203,359-byte gzip file. Its SHA-256, source URL, licence evidence, acquisition timestamp and robots response status are recorded in data/raw/snapshot_manifest.json. The raw host robots.txt returned HTTP 404: no robots restrictions were published there; the explicit repository licence is the basis for dataset reuse. This does not authorize scraping BestBuy.com or downloading linked images. The source's image URLs point to another host and its image rights are not cleared by this check, so only URLs were retained.

The price values are historical source-catalogue figures in USD, not invented values and not represented as current sale offers. A source price observation date is unavailable; acquisition time is kept separately. Warranty and unsupplied specifications remain NULL. Only source model/UPC are included in technicalSpecs, not inferred specifications.

Sample: 5 products covering 5 categories; every sample has name, brand, description and price; no licensed local images yet. Full metadata extraction: 20 products per category, 100 total. Category assignment uses source taxonomy, excludes accessory leaves, and detects smartphone evidence instead of calling every cell phone a smartphone. Duplicate manufacturer/model pairs are skipped. Each record retains its source SKU, source category path and product URL. Product identity is stable in the external key registry.

Remaining source limitation: all 100 records lack cleared local images. Do not report Image Retrieval readiness or image display as achieved. A source with explicit product-image reuse permission, or individually licensed correctly matched replacement images, is still needed. If the user requires current prices instead of historical source prices, select a live permitted source before replacing this catalogue.

## Retailer pilot after the user's updated source instruction

The user subsequently selected CellphoneS or FPT Shop for this local coursework and requested product images. This supersedes the previous open-licence-only acquisition preference; it does not cause retailer content to be labelled CC0 or openly licensed.

Checked public catalogue/product pages and these robots policies:

- https://cellphones.com.vn/robots.txt
- https://fptshop.com.vn/robots.txt
- Media-host robots responses are retained in `data/retailer_sample/source_policy_checks.json`.

Only ordinary public product URLs and their declared image URLs were accessed, with a descriptive user agent, a two-second delay, no authentication and no bypass of rate/access controls. Category aggregate prices were explicitly rejected. Product JSON-LD supplies matching name, brand, VND offer price, image and available specifications. Review authors and customer data are excluded from saved extracts.

Pilot result: four products with four valid downloaded images; all four have a source price. A fifth attempted product URL returned 404 and was not fabricated or replaced by an unrelated item. Product names, source links and prices are in `data/retailer_sample/products.json`; image URL, local file, dimensions, format and SHA-256 are in `images_manifest.json`. Open `data/retailer_sample/index.html` to inspect the local gallery. Eleven tests pass, including individual-offer parsing and rejection of category aggregate prices.

No retailer products or images have yet been imported into MySQL. The existing 100 historical records have not been overwritten. A choice between a separate retailer catalogue and exact-model enrichment of the old catalogue is pending the user's answer.


## Separate VND retailer catalogue

The user-selected new catalogue is complete in `ecommerce_vn_retailer_demo`: 100 products, 20 per category, all with VND source prices and downloaded main images. CellphoneS is supplemented by FPT Shop for smartwatches. The original 100-product database was preserved and checked by full row fingerprint; repeat import is unchanged. See [retailer catalogue](retailer_catalog.md) for commands, measured limitations and reports. Open `data/retailer_catalog/index.html` to view images.

# Confirmed brand and ranking-label review — 2026-11-04

The user confirmed that product 79 is Beats, that promotional suffixes such as `Chính hãng` do not define a separate brand, and that the remaining proposed relevance labels are correct.

## Applied data corrections

- Product 79: `Apple Chính hãng` → `Beats`.
- Samsung promotional aliases: IDs 64, 69, 70 and 83 → `Samsung`.
- Apple promotional aliases: IDs 71–78 and 80 → `Apple`.
- Case-only canonical spelling: IDs 106 and 107, `Honor` → `HONOR`.

Sixteen brand fields changed in `data/retailer_catalog/products.json` and the approved retailer database `ecommerce_vn_retailer_demo`. Product IDs, names, images, prices and specifications were retained. The raw `provenance.json` records remain unchanged for source traceability. Snapshots of the previous products file, database rows and embedding manifest are retained in `data/retailer_catalog/brand_review_backup_20261104T035211672203Z`.

`config/brands.py` defines canonical brand labels. Search conditions, catalogue filtering, public product output and brand dropdown generation use the same equivalence rule. Thus a legacy stored or submitted `Samsung Chính hãng` matches `Samsung`, and equivalent dropdown labels are deduplicated. A genuine Samsung/Apple mismatch is still rejected. Retailer collection normalizes promotional suffixes for future records; the explicit product-79 correction is recorded separately rather than treating all Apple-labelled products as Beats.

Because brand participates in the product-text representation and source fingerprint, embeddings for all sixteen changed records were regenerated. Preparation finished with 100 represented products and zero failures. A new backend process is required to clear older query/criteria caches and load the normalization code.

## Ranking relevance confirmation

The existing 60 catalogue-derived relevance cases are marked reviewed based on the user's explicit confirmation. Mixed-image queries use the corrected canonical brand, including Beats for source 79. Their relevant product IDs, group assignments and validation/test split are retained. A copy of the original unreviewed file is kept as `data/evaluation/ranking_review/cases_before_user_confirmation.json`.

`data/evaluation/ranking_review/index.html`, `review.md` and `catalogue_audit.json` reflect the confirmation. The twelve incomplete customer stress-query drafts remain unreviewed and are not included in scoring. Confirming the catalogue cases does not supply external photographs or verify missing product colours.

The reviewed grid experiment is stored separately in `data/evaluation/grid_reviewed_20261104`. It uses the corrected catalogue and regenerated embeddings, so its model/source fingerprints differ from the retained exploratory reports. It does not automatically change live ranking weights.

## Verification

The full Python suite passes 92 tests, including actual MySQL/HTTP checks for equivalent suffix aliases, dropdown deduplication, canonical criteria, conflicting real brands and product 79 belonging to Beats instead of Apple. The test databases are separate from the retailer demo and retained. No historical-catalogue database or user file was deleted.

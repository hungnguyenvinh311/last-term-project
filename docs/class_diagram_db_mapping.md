# Class diagram to MySQL mapping — review before implementation

Status: user approved integer articleID and file manifests for extra images/provenance. Product/category code and additive SQL are prepared. No existing diagram or database has been changed. Source selection for priced data is under evaluation.

## 1. Inputs actually inspected

- `../VPC4 Project/design class diagram.vpp`: the 14 entity classes, attributes, inheritance and 12 associations were read from the native project's model definitions; file last modified 2026-10-28.
- `../figures/design class diagram.jpg`: visually inspected and consistent with the above classes, including Product's two conflicting identifiers.
- `../VPC4 Project/database diagram.vpp`: 14 relational tables, their columns, PK/FK metadata; file last modified 2026-10-29. This is a relational reference, not a replacement for the entity diagram.
- `../search-system/backend/db/schema.sql` and that project's README: existing application is PostgreSQL/pgvector with a fashion catalogue. It is a separate project. Creating a MySQL catalogue here will not automatically populate or reconfigure its database.
- `AGENT_ECOMMERCE_CRAWL_MYSQL_CLASS_DIAGRAM.md`: requested sequence, crawl restrictions and deliverables.

The older `../new class diagram.jpg` and generic Markdown diagrams are not used to resolve discrepancies against these newer native files.

## 2. Persistent entities and proposed mapping

Identifiers shown as Integer map to `INT UNSIGNED` with consistent FK types. Money maps to `DECIMAL(18,2)`, not FLOAT. Dates use DATETIME or DATE as appropriate. All tables use InnoDB and utf8mb4. The names below follow the existing VP database diagram; spelling corrections are proposals rather than silently applied changes.

| Entity | Existing VP table | Columns and proposed MySQL representation | Key/relationship |
|---|---|---|---|
| Customer | Customer | customerID INT; fullName VARCHAR(255); email VARCHAR(254); Age INT versus database dateOfBirth DATE requires an explicit mapping decision; phoneNumber VARCHAR(32); shippingAddress TEXT | PK customerID; referenced by carts, orders and queries. |
| Category | Categories | categoryID INT; groupName VARCHAR(100); subCategory VARCHAR(100); specificationSchema JSON or TEXT | PK categoryID; Product category association becomes categoryID FK. These fields do not prescribe actual catalogue categories. |
| Product | Products | articleID INT versus articleId VARCHAR: disputed; productName VARCHAR(255); brand VARCHAR(120); description TEXT; technicalSpecs JSON/TEXT; warrantyTerms TEXT; imagePath VARCHAR(2048); price DECIMAL(18,2) nullable when genuinely missing; currency CHAR(3) nullable with absent price; isActive BOOLEAN; imageEmbedding JSON NULL; textEmbedding JSON NULL; representationUpdateAt DATETIME NULL; categoryID INT | Product key choice must be confirmed. categoryID FK NOT NULL preserves one category per product. Diagram has no ProductImage or CrawlSource entity. |
| Cart | Cart | cartID INT; customerID INT; createdAt DATETIME; updatedAt DATETIME from relational reference | PK cartID; customerID FK NOT NULL and UNIQUE enforces at most one cart/customer. items is mapped via CartItems, not serialized into Cart. |
| CartItem | CartItems | cartItemID INT; cartID INT; articleID matching Product key; quantity INT | PK cartItemID; FKs cartID, articleID; UNIQUE(cartID, articleID). Existing `articledID` appears misspelled. |
| Order | Orders | orderID INT; nullable customerID INT; status VARCHAR(40); totalAmount DECIMAL; shippingAddress TEXT; recipientPhone VARCHAR(32); currency CHAR(3); holdExpiresAt DATETIME; relational reference also contains paymentMethod, itemSubTotal, discountAmount, shippingFee, createdAt | PK orderID; optional customer FK follows the analysis/design multiplicity. items maps via OrderItems. Relational `holdExpireAt` and class `holdExpiresAt` differ. |
| OrderItem | OrderItems | orderItemID INT; orderID INT; articleID matching Product key; quantity INT; unitPrice DECIMAL; specificationSnapshot JSON/TEXT; warrantySnapshot TEXT; productNameSnapshot VARCHAR(255) exists in relational reference only | PK orderItemID; FKs orderID and articleID. |
| Payment | Payments | paymentID INT; orderID INT; paymentMethod VARCHAR(40); amount DECIMAL; status VARCHAR(40); transactionCode VARCHAR(255); paidAt DATETIME NULL; currency CHAR(3) appears in relational reference only | PK paymentID; orderID FK NOT NULL UNIQUE, one summary per order at most. Class spells the method `payMentMethod`. |
| Shipment | Shipments | shipmentID INT; orderID INT; trackingNumber VARCHAR(255); status VARCHAR(40); carrier VARCHAR(120); estimatedDeliveryDate DATETIME NULL; deliveredAt DATETIME NULL | PK shipmentID; orderID FK NOT NULL UNIQUE. Relational diagram spells identifier `shippingID`. |
| SearchQuery | searchQueries | queryID INT; customerID INT NULL; createdAt DATETIME; searchCriteria JSON/TEXT; queryType discriminator from relational design; sessionID INT in class but absent from relational design | PK queryID; optional customer FK. `creatAt` is a spelling variation. Session storage is not invented. |
| TextQuery | textQueries | query_id INT; queryText TEXT | query_id is both PK and FK to searchQueries(queryID). |
| ImageQuery | imageQueries | query_id INT; imageReference VARCHAR(2048); selectedRegion JSON/TEXT NULL | query_id is both PK and FK. Region stores coordinates, not an image. |
| VoiceQuery | voiceQueries | query_id INT; audioReference VARCHAR(2048) NULL; transcribedText TEXT | query_id is both PK and FK. Class spells text `transcribeText`. |
| SearchResult | seachResults | queryID INT; articleID matching Product key; rank INT; score DOUBLE | Composite PK(queryID, articleID); both are FKs; UNIQUE(queryID, rank). Proposed spelling correction: SearchResults. |

View, controller, Service, DAO and DAOImpl classes are not tables. Candidate vectors, result DTOs and crawler configuration are transient values. This task does not create customer/order/query demo records merely to fill unrelated tables.

## 3. Relationships

| Diagram relationship | Relational enforcement |
|---|---|
| Category 1 — Product 0..* | Products.categoryID NOT NULL FK; no category-less product. |
| Customer 1 — Cart 0..1 | Cart.customerID NOT NULL UNIQUE FK. |
| Customer 0..1 — Order 0..* | Orders.customerID nullable FK. |
| Customer 0..1 — SearchQuery 0..* | searchQueries.customerID nullable FK. |
| Cart 1 composition CartItem 0..* | CartItems.cartID FK NOT NULL. |
| Order 1 composition OrderItem 1..* | OrderItems.orderID FK NOT NULL; nonempty submitted orders require application transaction validation. |
| Product 1 — CartItem/OrderItem/SearchResult 0..* | Each child references exactly one Product key. |
| SearchQuery 1 composition SearchResult 0..* | SearchResult.queryID NOT NULL FK. |
| Order 1 — Payment/Shipment 0..1 | Unique orderID FK in each summary table. |
| TextQuery/ImageQuery/VoiceQuery extends SearchQuery | Shared-key subtype tables. |

Composition is business ownership, not automatic approval for destructive cascades. Existing financial/order data must not be deleted by an importer.

## 4. Inheritance choice

- Single table: simpler reads, but mixes text/image/audio nullable fields and diverges from the existing relational diagram.
- Joined subtype tables: preserves the three query classes and current VP tables; queries require joins. **Proposed choice.**
- Concrete subtype tables: duplicates common query columns and complicates a single SearchResult reference.

The importer for products never creates queries. A future query writer must transactionally create a parent and exactly one matching subtype; separate FKs alone do not enforce this exclusive choice. No trigger or claim of enforcement is assumed before implementation.

## 5. Minimal change proposals requiring a decision

### P1 — Product identifier

Current: Product has articleId String and articleID Integer, while VP Products uses integer articleID and SearchResult still labels articleId String.

Proposal: use Products.articleID INT as the internal key consistently in all FKs; retain external source IDs and source URLs in provenance files keyed by articleID. This resolves ambiguity without adding a domain class. Alternative: use one string key consistently, but that diverges from the latest relational key type. No diagram is modified before approval.

### P2 — Multiple images and provenance

Current: Product.imagePath represents one main image. There is no place for multiple image rows or source/licence details.

Minimal proposal: retain one main image in Product.imagePath and store a provenance manifest plus an image manifest in `data/`, linking each item and image to the product key. This adds no database entity. If multiple images must be queried directly from MySQL, propose **one new ProductImage class/table** with FK to Product; that design change needs approval. Do not repurpose imagePath as a JSON array silently.

### Other differences

- Product Float[] embeddings were extracted as Float from the native model property, while the exported image explicitly shows arrays. Treat these as optional arrays; proposed storage is nullable JSON, not assumed VECTOR support. No embeddings are generated in this crawl stage. Future generation must record actual model/dimension and use compatible query vectors, with similarity computed in application code.
- `technicalSpecs` versus relational `techicalSpecs`, `seachResults`, `articledID`, `shipmentID` versus `shippingID`, and other case/spelling differences must be listed in a naming map before generating SQL.
- Customer age versus birth date, SearchQuery sessionID absent from the database, and extra relational order/payment columns are out-of-product-scope discrepancies. A product/category-only first schema avoids silently deciding these unrelated mappings.
- Missing prices, warranty or technical specifications remain NULL/missing. No synthetic shop prices or warranty terms are assigned to real products.
- Source IDs are not necessarily unique across providers; deduplication uses provider + source item ID and preserves a persistent key map across import runs.

## 6. MySQL environment checked

- Windows service `MySQL97` is Running.
- `C:/Program Files/MySQL/MySQL Server 9.7/bin/mysql.exe --version` reports MySQL client 9.7.0.
- The unqualified `mysql` command instead resolves to `C:/xampp/mysql/bin/mysql.exe`, MariaDB 10.4.32. Use the explicit MySQL path.
- A read-only version query to localhost:3306 as root without a password failed with Access denied. Therefore server SQL version, grants, existing schemas and permissions are **not yet verified**. A client version is not evidence of the server version.
- No database was created or modified; no credential has been logged.

## 7. Proposed implementation layout

```text
docs/                    mapping, source assessment, setup and measured validation
database/                additive development DDL and example SELECT queries
crawler/
  config/                environment parsing and category/source settings
  sources/               provider-specific fetchers
  normalization/         source-to-approved-schema conversion
  media/                 download, validation, licences and image deduplication
  storage/               raw and normalized files/checkpoints
  database/              MySQL connections and transactional upsert importer
  validation/            coverage, duplicate, file and database checks
  cli.py                 explicit stage commands
tests/                   normalization, reimport and integrity checks
data/raw/                untouched source responses
data/normalized/         product/category data and provenance/key manifests
data/images/             permitted product images
.env.example             placeholders only
requirements.txt         dependencies for this project only
```

Catalogue implementation uses the approved integer ID and one-main-image design. database/001_catalog.sql covers Product and Category only; unrelated entity discrepancies remain explicitly unresolved. This directory is independent of the PostgreSQL search-system application.

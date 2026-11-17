-- Catalogue scope only: other entity mappings require separate resolution.
-- Run in a new development database, never a production/shared schema.
CREATE TABLE IF NOT EXISTS Categories (
  categoryID INT UNSIGNED NOT NULL,
  groupName VARCHAR(100) NOT NULL,
  subCategory VARCHAR(100) NOT NULL,
  specificationSchema JSON NULL,
  PRIMARY KEY (categoryID),
  UNIQUE KEY uq_category (groupName, subCategory)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS Products (
  articleID INT UNSIGNED NOT NULL,
  categoryID INT UNSIGNED NOT NULL,
  productName VARCHAR(255) NOT NULL,
  brand VARCHAR(120) NULL,
  description TEXT NULL,
  technicalSpecs JSON NULL,
  warrantyTerms TEXT NULL,
  imagePath VARCHAR(2048) NULL,
  price DECIMAL(18,2) NULL,
  currency CHAR(3) NULL,
  isActive BOOLEAN NOT NULL DEFAULT TRUE,
  imageEmbedding JSON NULL,
  textEmbedding JSON NULL,
  representationUpdateAt DATETIME NULL,
  PRIMARY KEY (articleID),
  CONSTRAINT fk_product_category FOREIGN KEY (categoryID)
    REFERENCES Categories(categoryID) ON DELETE RESTRICT,
  CONSTRAINT ck_price CHECK (price IS NULL OR price >= 0),
  CONSTRAINT ck_price_currency CHECK ((price IS NULL AND currency IS NULL)
    OR (price IS NOT NULL AND currency IS NOT NULL)),
  KEY idx_product_category_price (categoryID, price),
  KEY idx_product_brand (brand),
  KEY idx_product_name (productName)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

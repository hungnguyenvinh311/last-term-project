-- Set the agreed warranty text for existing products.
UPDATE Products
SET warrantyTerms='Bảo hành 12 tháng';

UPDATE Products
SET technicalSpecs=JSON_SET(
  COALESCE(technicalSpecs,JSON_OBJECT()),
  '$."Số lượng khả dụng (minh họa)"',
  1 + MOD(articleID * 7,30)
)
WHERE JSON_EXTRACT(COALESCE(technicalSpecs,JSON_OBJECT()), '$."Số lượng khả dụng (minh họa)"') IS NULL;

SELECT c.subCategory, COUNT(p.articleID) AS products
FROM Categories c LEFT JOIN Products p ON p.categoryID=c.categoryID
GROUP BY c.categoryID,c.subCategory;
SELECT articleID,productName,brand,price,currency FROM Products
WHERE price BETWEEN 100 AND 500 AND currency='USD' ORDER BY price;
SELECT articleID,productName FROM Products WHERE productName LIKE '%Samsung%';
SELECT articleID,imagePath FROM Products WHERE articleID=1;
SELECT COUNT(*) AS orphan_products FROM Products p
LEFT JOIN Categories c ON c.categoryID=p.categoryID WHERE c.categoryID IS NULL;
-- Additional licensed images and provenance are in data/normalized/images_manifest.json.

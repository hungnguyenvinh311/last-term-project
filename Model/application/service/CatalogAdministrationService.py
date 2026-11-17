from Model.application.errors import DomainError
from Model.application.service.ProductService import public_product
from DAO.contract.ProductDAO import ProductDAO
from DAO.contract.CategoryDAO import CategoryDAO
from Model.application.contract.IMediaStorage import IMediaStorage


class CatalogAdministrationService:
    def __init__(self, products:ProductDAO, categories:CategoryDAO, media:IMediaStorage, changed=lambda articleID: None):
        self.products, self.categoryDAO, self.media, self.changed = products, categories, media, changed

    def listProducts(self): return [public_product(p) for p in self.products.findAll()]
    def categories(self): return self.categoryDAO.findAll()

    def saveProduct(self, values, articleID=None, actorID=None):
        if values.get('categoryID') not in {r['categoryID'] for r in self.categories()}:
            raise DomainError('Danh mục không tồn tại')
        before = self.products.findById(articleID) if articleID else None
        row = self.products.save(values, articleID, actorID)
        if before and any(before[k] != row[k] for k in ('categoryID','imagePath')):
            self.changed(row['articleID'])
        return public_product(row)

    def archiveProduct(self, articleID, actorID=None): return public_product(self.products.save({'isActive':False}, articleID, actorID))

    def updateCategory(self, categoryID, values, actorID=None): return self.categoryDAO.update(categoryID, values, actorID)

    def uploadImage(self, articleID, content):
        if not self.products.findById(articleID): raise DomainError('Không tìm thấy sản phẩm', 404)
        reference = self.media.saveProductImage(content)
        row = self.products.save({'imagePath':reference}, articleID)
        self.changed(articleID)
        return public_product(row)

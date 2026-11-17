from Model.application.errors import DomainError
class CartService:
    def __init__(self,carts,customers,products,pricing=None):
        from .CheckoutPricingService import CheckoutPricingService
        self.carts,self.customers,self.products=carts,customers,products
        self.pricing=pricing or CheckoutPricingService()
    def getCart(self,customerID):
        cart=self.carts.getCart(customerID)
        return {**cart,'pricing':self.pricing.calculate(cart['items'])}
    def addItem(self,customerID,articleID,quantity):
        if not 1<=quantity<=99: raise DomainError('Số lượng phải từ 1 đến 99')
        if not self.customers.findById(customerID): raise DomainError('Không tìm thấy khách hàng',404)
        return self.carts.save(customerID,articleID,quantity,add=True)
    def changeQuantity(self,customerID,articleID,quantity):
        if not 1<=quantity<=99: raise DomainError('Số lượng phải từ 1 đến 99')
        return self.carts.save(customerID,articleID,quantity)
    def removeItem(self,customerID,articleID): return self.carts.save(customerID,articleID,0)

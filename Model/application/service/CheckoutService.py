from Model.application.errors import DomainError
class CheckoutService:
    def __init__(self,orders,payment,fulfilment): self.orders,self.payment,self.fulfilment=orders,payment,fulfilment
    def submitCheckout(self,customerID,payload):
        address=str(payload.get('shippingAddress','')).strip();phone=str(payload.get('recipientPhone','')).strip()
        if not 5<=len(address)<=500 or not 8<=len(phone)<=30: raise DomainError('Nhập địa chỉ và số điện thoại hợp lệ')
        if payload.get('paymentMethod') not in {'ONLINE','COD'}: raise DomainError('Phương thức thanh toán không hợp lệ')
        return self.orders.createWithItems(customerID,{**payload,'shippingAddress':address,'recipientPhone':phone})
    def cancelBeforePacking(self,customerID,orderID):
        self.orders.cancel(customerID,orderID)
        return self.getOrder(customerID,orderID)
    def listOrders(self,customerID): return self.orders.listOwned(customerID)
    def getInvoice(self,customerID,orderID): return self.orders.getInvoice(orderID,customerID)
    def getOrder(self,customerID,orderID):
        order=self.orders.findOwned(customerID,orderID)
        return {**order,'payment':self.payment.getPaymentStatus(orderID),'shipment':self.fulfilment.getShipmentStatus(orderID)}
    def staffOrders(self): return self.orders.listAll()

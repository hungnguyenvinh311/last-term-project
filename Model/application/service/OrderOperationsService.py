from Model.application.errors import DomainError
from DAO.contract.OrderDAO import OrderDAO
from DAO.contract.CustomerDAO import CustomerDAO
from DAO.contract.PaymentDAO import PaymentDAO
from Model.application.contract.ICheckout import ICheckout


class OrderOperationsService:
    def __init__(self,orders:OrderDAO,customers:CustomerDAO,checkout:ICheckout,payments:PaymentDAO):
        self.orders,self.customers,self.checkout,self.payments=orders,customers,checkout,payments

    def details(self,orderID):
        order=self.orders.findById(orderID)
        if not order: raise DomainError('Không tìm thấy đơn hàng',404)
        return {**self.checkout.getOrder(order['customerID'],orderID),'customer':self.customers.findById(order['customerID'])}

    def cancel(self,orderID,actorID=None):
        row=self.details(orderID)
        self.orders.cancel(row['customerID'],orderID,actorID)
        return self.details(orderID)

    def confirmCOD(self,orderID,amount,trackingNumber,reference,actorID=None):
        return self.payments.confirmCOD(orderID,amount,trackingNumber,reference,actorID)

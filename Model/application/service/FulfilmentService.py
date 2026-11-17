from Model.application.errors import DomainError
class FulfilmentService:
    def __init__(self,shipments,orders,provider): self.shipments,self.orders,self.provider=shipments,orders,provider
    def createShipment(self,orderID,actorID=None):
        order=self.orders.findById(orderID)
        if not order: raise DomainError('Không tìm thấy đơn',404)
        outcome=self.provider.createShipment(orderID,order['shippingAddress'])
        return self.shipments.saveSummary(orderID,outcome,actorID)
    def getShipmentStatus(self,orderID): return self.shipments.findByOrder(orderID)
    def updateStatus(self,orderID,status,actorID=None):
        order=self.orders.findById(orderID)
        if not order: raise DomainError('Không tìm thấy đơn',404)
        transitions={'Confirmed':'Packing','Packing':'Packed','Packed':'Dispatched'}
        if order['status']!=status and transitions.get(order['status'])!=status:
            raise DomainError('Chuyển trạng thái không hợp lệ',409)
        self.createShipment(orderID,actorID)
        self.shipments.updateStatus(orderID,status,actorID)
        return self.getShipmentStatus(orderID)
    def confirmReceived(self,customerID,orderID):
        return self.shipments.confirmReceived(orderID,customerID)

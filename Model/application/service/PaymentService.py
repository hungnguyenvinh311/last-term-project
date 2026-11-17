from Model.application.errors import DomainError
class PaymentService:
    def __init__(self,payments,orders,gateway): self.payments,self.orders,self.gateway=payments,orders,gateway
    def recordStaffVerifiedOnlineResult(self,orderID,scenario,actorID=None,reference=None,eventKey=None):
        order=self.orders.findById(orderID)
        if not order: raise DomainError('Không tìm thấy đơn hàng',404)
        if order['paymentMethod']!='ONLINE': raise DomainError('Chỉ xác nhận kết quả cho đơn thanh toán online',409)
        if order['status']=='Cancelled': raise DomainError('Đơn đã hủy',409)
        current=self.payments.findByOrder(orderID)
        if current['status']=='Paid': return current
        outcome=self.gateway.processPayment(orderID,order['totalAmount'],scenario)
        if reference:
            outcome.transactionCode=reference
        return self.payments.saveSummary(orderID,outcome,actorID,reference,eventKey)
    def getPaymentStatus(self,orderID): return self.payments.findByOrder(orderID)

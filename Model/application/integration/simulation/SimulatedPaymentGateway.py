from Model.application.dto.PaymentOutcome import PaymentOutcome
from Model.application.errors import DomainError
class SimulatedPaymentGateway:
    def processPayment(self,orderId,amount,scenario):
        states={'success':'Paid','failure':'Failed','pending':'Pending'}
        if scenario not in states: raise DomainError('Kịch bản thanh toán không hợp lệ')
        return PaymentOutcome(orderId,amount,states[scenario],f'DEMO-{orderId}-{scenario}')

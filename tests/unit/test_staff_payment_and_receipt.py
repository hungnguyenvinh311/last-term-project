import pytest

from Model.application.errors import DomainError
from Model.application.service.FulfilmentService import FulfilmentService
from Model.application.service.PaymentService import PaymentService


class FakeOrders:
    def __init__(self, order):
        self.order = order

    def findById(self, order_id):
        return self.order if self.order and self.order['orderID'] == order_id else None


class FakePayments:
    def __init__(self, current):
        self.current = current
        self.saved = []

    def findByOrder(self, order_id):
        return self.current

    def saveSummary(self, order_id, outcome, actorID=None, reference=None, eventKey=None):
        self.saved.append((order_id, outcome))
        self.current = {'status': outcome.status, 'transactionCode': outcome.transactionCode}
        return self.current


class FakeGateway:
    def __init__(self):
        self.calls = []

    def processPayment(self, order_id, amount, scenario):
        self.calls.append((order_id, amount, scenario))
        return type('Outcome', (), {
            'orderID': order_id,
            'amount': amount,
            'status': {'success': 'Paid', 'failure': 'Failed', 'pending': 'Pending'}[scenario],
            'transactionCode': 'DEMO-'+str(order_id),
        })()


def service(order, payment):
    gateway = FakeGateway()
    return PaymentService(payment, FakeOrders(order), gateway), gateway


def test_online_result_can_only_be_recorded_through_staff_operation():
    payment = FakePayments({'status': 'Pending', 'transactionCode': None})
    api, gateway = service({'orderID': 8, 'paymentMethod': 'ONLINE', 'status': 'AwaitingPayment', 'totalAmount': 1200}, payment)

    result = api.recordStaffVerifiedOnlineResult(8, 'success')

    assert result['status'] == 'Paid'
    assert gateway.calls == [(8, 1200, 'success')]
    assert not hasattr(api, 'payOrder')


@pytest.mark.parametrize('order,current', [
    (None, {'status': 'Pending'}),
    ({'orderID': 8, 'paymentMethod': 'COD', 'status': 'Confirmed', 'totalAmount': 1200}, {'status': 'UnpaidCOD'}),
    ({'orderID': 8, 'paymentMethod': 'ONLINE', 'status': 'Cancelled', 'totalAmount': 1200}, {'status': 'Pending'}),
])
def test_staff_online_result_rejects_missing_cod_or_cancelled_order(order, current):
    api, gateway = service(order, FakePayments(current))

    with pytest.raises(DomainError):
        api.recordStaffVerifiedOnlineResult(8, 'success')

    assert gateway.calls == []


def test_paid_result_is_idempotent_and_pending_result_can_be_reconciled():
    paid = FakePayments({'status': 'Paid', 'transactionCode': 'BANK-1'})
    api, gateway = service({'orderID': 8, 'paymentMethod': 'ONLINE', 'status': 'Confirmed', 'totalAmount': 1200}, paid)
    assert api.recordStaffVerifiedOnlineResult(8, 'failure') == paid.current
    assert gateway.calls == []

    pending = FakePayments({'status': 'Pending', 'transactionCode': None})
    api, gateway = service({'orderID': 8, 'paymentMethod': 'ONLINE', 'status': 'AwaitingPayment', 'totalAmount': 1200}, pending)
    assert api.recordStaffVerifiedOnlineResult(8, 'pending')['status'] == 'Pending'
    assert api.recordStaffVerifiedOnlineResult(8, 'success')['status'] == 'Paid'
    assert [call[2] for call in gateway.calls] == ['pending', 'success']


def test_customer_delivery_confirmation_delegates_owner_and_order_to_persistence():
    class Shipments:
        def confirmReceived(self, order_id, customer_id):
            return {'orderID': order_id, 'customerID': customer_id, 'status': 'Delivered'}

    api = FulfilmentService(Shipments(), None, None)
    assert api.confirmReceived(55, 8) == {'orderID': 8, 'customerID': 55, 'status': 'Delivered'}

from datetime import date
from contextlib import contextmanager

from DAO.application.dao.ReportDAOImpl import ReportDAOImpl
from Model.application.service.ReportingService import ReportingService


class InventoryLedgerDAO:
    def __init__(self, row):
        self.row = row

    def inventoryRead(self, start, end, categoryID=None):
        return [self.row], []


def test_receipt_during_period_increases_received_and_closing_not_opening():
    before_receipt = ReportingService(InventoryLedgerDAO({
        'articleID': 1, 'brand': 'Samsung', 'openingQuantity': 10,
        'receivedInPeriod': 0, 'dispatchedInPeriod': 0,
        'adjustmentsInPeriod': 0, 'onHandQuantity': 10, 'committedQuantity': 0,
    })).inventory(date(2026, 11, 1), date(2026, 11, 30))['products'][0]

    after_receipt = ReportingService(InventoryLedgerDAO({
        'articleID': 1, 'brand': 'Samsung', 'openingQuantity': 10,
        'receivedInPeriod': 3, 'dispatchedInPeriod': 0,
        'adjustmentsInPeriod': 0, 'onHandQuantity': 13, 'committedQuantity': 0,
    })).inventory(date(2026, 11, 1), date(2026, 11, 30))['products'][0]

    assert before_receipt['openingQuantity'] == after_receipt['openingQuantity'] == 10
    assert after_receipt['receivedInPeriod'] == 3
    assert before_receipt['closingQuantity'] == 10
    assert after_receipt['closingQuantity'] == 13
    assert after_receipt['currentAvailableQuantity'] == 13


def test_available_now_subtracts_active_commitments_without_changing_period_closing():
    product = ReportingService(InventoryLedgerDAO({
        'articleID': 2, 'brand': 'Apple', 'openingQuantity': 8,
        'receivedInPeriod': 4, 'dispatchedInPeriod': 2,
        'adjustmentsInPeriod': -1, 'onHandQuantity': 9, 'committedQuantity': 3,
    })).inventory(date(2026, 11, 1), date(2026, 11, 30))['products'][0]

    assert product['closingQuantity'] == 9
    assert product['currentAvailableQuantity'] == 6


def test_inventory_opening_query_uses_period_start_to_reverse_receipts():
    class DB:
        def __init__(self):
            self.calls = []

        @contextmanager
        def transaction(self):
            yield object()

        def query(self, sql, params=(), connection=None, one=False):
            self.calls.append((sql, params))
            return []

    db = DB()
    start, end = date(2026, 11, 1), date(2026, 12, 1)

    ReportDAOImpl(db).inventoryRead(start, end)

    row_sql, row_params = db.calls[0]
    assert 'sm.occurredAt>=%s AND sm.type IN (\'IN\',\'OUT\',\'ADJUSTMENT\')' in row_sql
    # The seventh placeholder is the Opening cutoff, so movements from the
    # selected period start (including receipts) are reversed from on-hand.
    assert row_params == (start, end, start, end, start, end, start)

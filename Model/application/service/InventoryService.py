from Model.application.contract.IInventory import IInventory
from Model.application.errors import DomainError


class InventoryService(IInventory):
    def __init__(self, dao):
        self.dao = dao

    def listStock(self):
        return self.dao.listAll()

    def receiveStock(self, receiptNumber, items, actorID):
        receiptNumber = str(receiptNumber or '').strip()
        if not 3 <= len(receiptNumber) <= 255:
            raise DomainError('Receipt number must contain 3 to 255 characters')
        return self.dao.receive(receiptNumber, items, actorID)

    def adjustStock(self, articleID, delta, reason, actorID):
        if not isinstance(delta, int) or abs(delta) > 100000:
            raise DomainError('Adjustment quantity must be a bounded integer')
        return self.dao.adjust(articleID, delta, reason, actorID)

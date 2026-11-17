from abc import ABC, abstractmethod


class InventoryDAO(ABC):
    @abstractmethod
    def listAll(self): ...

    @abstractmethod
    def receive(self, receiptNumber, items, actorID): ...

    @abstractmethod
    def adjust(self, articleID, delta, reason, actorID): ...

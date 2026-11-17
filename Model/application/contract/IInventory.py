from abc import ABC, abstractmethod


class IInventory(ABC):
    @abstractmethod
    def listStock(self): ...

    @abstractmethod
    def receiveStock(self, receiptNumber, items, actorID): ...

    @abstractmethod
    def adjustStock(self, articleID, delta, reason, actorID): ...

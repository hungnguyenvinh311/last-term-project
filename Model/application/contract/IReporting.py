from typing import Protocol


class IReporting(Protocol):
    def sales(self,start,end,**filters): ...

from typing import Protocol


class IReportExport(Protocol):
    def export(self,report:dict,format:str)->bytes: ...

from typing import Protocol


class ReportDAO(Protocol):
    def read(self, start, end): ...

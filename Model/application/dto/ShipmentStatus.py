from dataclasses import dataclass
@dataclass
class ShipmentStatus:
    trackingNumber: str
    carrier: str = 'Coursework simulator'
    status: str = 'Created'

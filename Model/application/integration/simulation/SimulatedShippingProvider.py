from Model.application.dto.ShipmentStatus import ShipmentStatus
class SimulatedShippingProvider:
    def createShipment(self,orderId,address): return ShipmentStatus(f'DEMO-SHIP-{orderId}')
    def getStatus(self,trackingNumber): return ShipmentStatus(trackingNumber)

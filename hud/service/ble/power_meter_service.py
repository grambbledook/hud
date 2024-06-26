from PySide6.QtCore import QThreadPool

from hud.model.data_classes import Device
from hud.model.events import PowerMeasurement, MeasurementEvent
from hud.model.model import Model
from hud.service.ble.base_ble_connection_service import BaseConnectionService
from hud.service.device_registry import DeviceRegistry


class PowerService(BaseConnectionService):
    def __init__(self, pool: QThreadPool, model: Model, registry: DeviceRegistry):
        super().__init__(pool, model, registry)

    async def process_supported_features(self, _, device: Device):
        self.model.set_power(device)

    def process_measurement(self, device: Device, data: bytearray):
        # GATT Specification Supplement v5: 3.59.2
        power = int.from_bytes(data[2:4], byteorder='little', signed=True)

        event = MeasurementEvent(device=device, measurement=PowerMeasurement(power))
        self.model.update_power(event)

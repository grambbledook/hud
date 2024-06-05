from PySide6.QtCore import QThreadPool

from hud.model import HRM
from hud.model.data_classes import Device
from hud.model.events import MeasurementEvent, HrMeasurement
from hud.model.model import Model
from hud.service.ble.base_ble_connection_service import BaseConnectionService
from hud.service.device_registry import DeviceRegistry


class HeartRateService(BaseConnectionService):
    def __init__(self, model: Model, registry: DeviceRegistry):
        super().__init__(model, registry, service=HRM)

    async def process_feature_and_set_devices(self, _, device: Device):
        self.model.set_hrm(device)

    def process_measurement(self, device: Device, data: bytearray):
        # GATT Specification Supplement v5: 3.106.2
        flag = data[0]

        if flag & 0x01:
            hrm = int.from_bytes(data[1:3], byteorder='little', signed=False)
        else:
            hrm = int.from_bytes(data[1:2], byteorder='little', signed=False)

        event = MeasurementEvent(device=device, measurement=HrMeasurement(hrm))
        self.model.update_hrm(event)

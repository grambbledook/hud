from PySide6.QtCore import QThreadPool
from bleak import BleakClient

from hud.model.data_classes import Device
from hud.model.model import Model
from hud.service.ble.base_ble_connection_service import BaseConnectionService
from hud.service.device_registry import DeviceRegistry


class FecBikeTrainerService(BaseConnectionService):

    def __init__(self, pool: QThreadPool, model: Model, registry: DeviceRegistry):
        super().__init__(pool, model, registry)

    async def process_supported_features(self, client: BleakClient, device: Device):
        self.model.set_bike_trainer(device)

    def process_measurement(self, device: Device, data: bytearray):
        print(f"Received data from {device}: {data}")

    def set_target_power(self, device: Device, target_power: int):
        pass

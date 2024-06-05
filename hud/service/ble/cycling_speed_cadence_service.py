from PySide6.QtCore import QThreadPool
from bleak import BleakClient

from hud.model import CSC
from hud.model.data_classes import Device
from hud.model.events import SpeedMeasurement, CadenceMeasurement, MeasurementEvent
from hud.model.model import Model
from hud.service.ble.base_ble_connection_service import BaseConnectionService
from hud.service.ble.ble_client import BleClient
from hud.service.device_registry import DeviceRegistry


class CyclingCadenceAndSpeedService(BaseConnectionService):
    CSC_FEATURE_UUID = "00002a5c-0000-1000-8000-00805f9b34fb"

    def __init__(self, model: Model, registry: DeviceRegistry):
        super().__init__(model, registry, service=CSC)

    async def process_feature_and_set_devices(self, client: BleClient, device: Device):
        supported_services = await self.parse_csc_feature(client)

        for supported_service in supported_services:
            match supported_service:
                case "cadence":
                    self.model.set_cadence(device)
                case "speed":
                    self.model.set_speed(device)
                case _:
                    print(f"Unknown service: {supported_service}")

    async def parse_csc_feature(self, client: BleClient) -> list[str]:
        if not client.is_connected:
            await client.connect()

        data = await client.read_gatt_char(self.CSC_FEATURE_UUID)
        flag = int.from_bytes(data[0:1], byteorder='little', signed=False)

        result = []
        if flag & 0b01:
            result.append("speed")

        if flag & 0b10:
            result.append("cadence")
        return result

    def process_measurement(self, device: Device, data: bytearray):
        # GATT Specification Supplement v5: 3.55.2
        flag = data[0]

        offset = 1

        if flag & 0b01:
            cwr = int.from_bytes(data[0 + offset:4 + offset], byteorder='little', signed=False)
            lwet = int.from_bytes(data[4 + offset:6 + offset], byteorder='little', signed=False)
            offset += 6

            csc_event = MeasurementEvent(device=device, measurement=SpeedMeasurement(cwr, lwet))
            self.model.update_speed(csc_event)

        if flag & 0b10:
            ccr = int.from_bytes(data[0 + offset:2 + offset], byteorder='little', signed=False)
            lcet = int.from_bytes(data[2 + offset:4 + offset], byteorder='little', signed=False)

            csc_event = MeasurementEvent(device=device, measurement=CadenceMeasurement(ccr, lcet))
            self.model.update_cadence(csc_event)

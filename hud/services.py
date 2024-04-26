import asyncio
from typing import Callable, TypeVar, AsyncGenerator, Tuple

from PyQt5.QtCore import QRunnable, QThreadPool
from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic

from hud.devices import SUPPORTED_SERVICES, Service
from hud.events import MeasurementEvent, SpeedMeasurement, CadenceMeasurement
from hud.models import Model, Device

T = TypeVar('T')


# # # # # # # # # # # # # # # # # # # # # # #
# BLE Device Discovery
# # # # # # # # # # # # # # # # # # # # # # #
class ScanTask(QRunnable):

    def __init__(self, services: list[Service], publish_device: Callable[[Device], None], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.services = services
        self.publish_device = publish_device

    def run(self):
        asyncio.run(self.scan())

    async def scan(self):
        scanner = BleakScanner()

        for _ in range(5):
            await self._do_scan(scanner)

    async def _do_scan(self, scanner: BleakScanner):
        supported_services = dict(map(lambda s: (s.service_uuid, s), self.services))

        address_to_device_and_advertisement_data = await scanner.discover(return_adv=True)
        for device, advertisement_data in address_to_device_and_advertisement_data.values():
            for service_uuid in set(supported_services) & set(advertisement_data.service_uuids):
                device = Device(device.name, device.address, supported_services[service_uuid])

                self.publish_device(device)


class BleDiscoveryService:

    def __init__(self, pool: QThreadPool, model: Model):
        self.pool = pool
        self.model = model

    def start_scan(self):
        task = ScanTask(SUPPORTED_SERVICES, self._append_device)
        self.pool.start(task)

    def _append_device(self, device: Device):
        if device in self.model.devices:
            return

        self.model.devices.append(device)


# # # # # # # # # # # # # # # # # # # # # # #
# BLE Notification Handling
# # # # # # # # # # # # # # # # # # # # # # #
class MeasurementReadingTask(QRunnable):

    def __init__(
            self,
            device: Device,
            feature_extractor: Callable[[BleakClient, Device], object],
            event_processor: Callable[[object, bytearray], None],
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.device = device
        self.feature_extractor = feature_extractor
        self.callback = event_processor
        self.client = None
        self._is_active = True

    def run(self):
        asyncio.run(self.execute())

    async def execute(self):
        self.client = BleakClient(self.device.address)
        await self.feature_extractor(self.client, self.device)
        async for value in self.start():
            if self._is_active == False:
                break
            self.callback(*value)

    async def start(self) -> AsyncGenerator[Tuple[BleakGATTCharacteristic, bytearray], None]:
        queue = asyncio.Queue()

        async def on_data(characteristic: BleakGATTCharacteristic, data: bytearray):
            await queue.put((characteristic, data))

        if not self.client.is_connected:
            print(f"Connecting to {self.device.name}")
            await self.client.connect()
        print(f"Subscribing for {self.device.service.characteristic_uuid}")
        await self.client.start_notify(self.device.service.characteristic_uuid, callback=on_data)
        print(f"Subscribed for {self.device.service.characteristic_uuid}")

        while True:
            characteristic, data = await queue.get()
            queue.task_done()
            yield self.device, data

    def unsubscribe(self):
        self._is_active = False
        self.client.stop_notify(self.device.service.characteristic_uuid)
        self.client.disconnect()


class CyclingCadenceAndSpeedService:
    CSC_FEATURE_UUID = "00002a5c-0000-1000-8000-00805f9b34fb"

    def __init__(self, pool: QThreadPool, model: Model):
        self.pool = pool
        self.model = model

    def set_device(self, device: Device):
        task = MeasurementReadingTask(
            device,
            feature_extractor=self.process_supported_features,
            event_processor=self.process_measurement,
        )
        self.pool.start(task)

    async def process_supported_features(self, client: BleakClient, device: Device):

        supported_services = await self.parse_csc_feature(client)

        for supported_service in supported_services:
            match supported_service:
                case "cadence":
                    self.model.set_cadence(device)
                case "speed":
                    self.model.set_speed(device)
                case _:
                    print(f"Unknown service: {supported_service}")

    async def parse_csc_feature(self, client: BleakClient) -> list[str]:
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
        flag = int.from_bytes(data[0:1], byteorder='little', signed=False)
        value = int.from_bytes(data[1:], byteorder='little', signed=False)

        match flag:
            case 1:
                cwr = value & 0xFFFFFF
                lwet = value >> (4 * 8)

                new_cwr = int.from_bytes(data[1:5], byteorder='little', signed=False)
                new_lwet = int.from_bytes(data[5:7], byteorder='little', signed=False)

                print(f"Speed: cwr={cwr}, lwet={lwet}, new_cwr={new_cwr}, new_lwet={new_lwet}")

                cadence_event = MeasurementEvent(device=device, measurement=SpeedMeasurement(cwr, lwet))
                self.model.update_speed(cadence_event)

            case 2:
                ccr = value & 0xFFFF
                lcet = value >> (2 * 8)

                new_ccr = int.from_bytes(data[1:3], byteorder='little', signed=False)
                new_lcet = int.from_bytes(data[3:5], byteorder='little', signed=False)

                print(f"Cadence: ccr={ccr}, lcet={lcet}, new_ccr={new_ccr}, new_lcet={new_lcet}")

                cadence_event = MeasurementEvent(device=device, measurement=CadenceMeasurement(ccr, lcet))
                self.model.update_cadence(cadence_event)

            case 3:
                spd = value & 0xFFFFFFFFFFFF
                cwr = spd & 0xFFFFFF
                lwet = spd >> (4 * 8)

                new_cwr = int.from_bytes(data[1:5], byteorder='little', signed=False)
                new_lwet = int.from_bytes(data[5:7], byteorder='little', signed=False)
                print(f"> Speed: cwr={cwr}, lwet={lwet}, new_cwr={new_cwr}, new_lwet={new_lwet}")
                speed_event = MeasurementEvent(device=device, measurement=SpeedMeasurement(cwr, lwet))
                self.model.update_speed(speed_event)

                cad = value >> (6 * 8)

                ccr = cad & 0xFF
                lcet = cad >> 16

                new_ccr = int.from_bytes(data[7:9], byteorder='little', signed=False)
                new_lcet = int.from_bytes(data[9:11], byteorder='little', signed=False)
                print(f"> Cadence: ccr={ccr}, lcet={lcet}, new_ccr={new_ccr}, new_lcet={new_lcet}")
                cadence_event = MeasurementEvent(device=device, measurement=CadenceMeasurement(ccr, lcet))
                self.model.update_cadence(cadence_event)


#
# class SpeedService(BleDeviceService):
#     @dataclass
#     class State:
#         cum_wheel_revs: int
#         last_wheel_event_time: int
#
#     def __init__(self, pool: QThreadPool, listeners: Listeners):
#         self.pool = pool
#         self.listeners = listeners
#         self.state = SpeedService.State(0, 0)
#         self.active_device_connection = None
#
#     def start_scan(self, device_found: Channel):
#         task = ScanTask(SPEED_SENSOR, device_found)
#         self.pool.start(task)
#
#     def set_device(self, device: DeviceHandle):
#         if self.active_device_connection:
#             self.active_device_connection.close()
#
#         self.active_device_connection = MeasurementReadingTask(device, self._process_measurement)
#         self.pool.start(self.active_device_connection)
#
#     def _process_measurement(self, _, data):
#         flag = data[0]
#
#         if flag not in {1, 3}:
#             return
#         value = int.from_bytes(data[1:], byteorder='little', signed=False)
#
#         new_cwr = int.from_bytes(data[1:5], byteorder='little', signed=False)
#         new_lwet = int.from_bytes(data[5:7], byteorder='little', signed=False)
#         old_cwr = self.state.cum_wheel_revs
#         old_lwet = self.state.last_wheel_event_time
#         self.state.cum_wheel_revs, self.state.last_wheel_event_time = new_cwr, new_lwet
#
#         speed = (new_cwr - old_cwr) / (new_lwet - old_lwet)
#
#         self.listeners.notify(speed)
#
#
# class CadenceService(BleDeviceService):
#     @dataclass
#     class State:
#         prev_ccr: int
#         prev_lcet: int
#         last_ccr: int
#         last_lcet: int
#         cadence: int
#
#     def __init__(self, pool: QThreadPool, listeners: Listeners):
#         self.pool = pool
#         self.listeners = listeners
#         self.state = CadenceService.State(0, 0, 0, 0, 0)
#         self.active_device_connection = None
#
#     def start_scan(self, device_found: Channel):
#         task = ScanTask(SPEED_SENSOR, device_found)
#         self.pool.start(task)
#
#     def set_device(self, device: DeviceHandle):
#         if self.active_device_connection:
#             self.active_device_connection.close()
#
#         self.active_device_connection = MeasurementReadingTask(device, self._process_measurement)
#         self.pool.start(self.active_device_connection)
#
#     def _process_measurement(self, _, data):
#         flag = data[0]
#
#         match flag:
#             case 2:
#                 cur_ccr = int.from_bytes(data[1:3], byteorder='little', signed=False)
#                 cur_lcet = int.from_bytes(data[3:5], byteorder='little', signed=False)
#             case 3:
#                 cur_ccr = int.from_bytes(data[7:9], byteorder='little', signed=False)
#                 cur_lcet = int.from_bytes(data[9:11], byteorder='little', signed=False)
#             case _:
#                 return
#
#         if cur_lcet <= self.state.last_lcet:
#             return
#
#         self.state.prev_ccr, self.state.prev_lcet = self.state.last_ccr, self.state.last_lcet
#         self.state.last_ccr, self.state.last_lcet = cur_ccr, cur_lcet
#
#         cadence = (self.state.last_ccr - self.state.prev_ccr) / (
#                 self.state.last_lcet - self.state.prev_lcet) * 60 * 1000
#         self.state.cadence = cadence
#         self.listeners.notify(cadence)

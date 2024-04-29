import abc
import asyncio
from typing import Callable, TypeVar, AsyncGenerator, Tuple, Coroutine

from PyQt5.QtCore import QRunnable, QThreadPool
from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic

from hud.model import Model, Device, MeasurementEvent, SpeedMeasurement, CadenceMeasurement, HrmMeasurement, \
    SUPPORTED_SERVICES, Service

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
            feature_extractor: Callable[[BleakClient, Device], Coroutine[None, None, None]],
            event_processor: Callable[[Device, bytearray], None],
            disconnect_handler: Callable[[BleakClient], None] = None,
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.device = device
        self.feature_extractor = feature_extractor
        self.callback = event_processor
        self.disconnect_handler = disconnect_handler
        self.client = None
        self._is_active = True

    def run(self):
        asyncio.run(self.try_execute())

    async def try_execute(self):
        try:
            await self.connect()
            await self.extract_features()
            await self.subscribe_to_events()
        except Exception as e:
            print(f"An error occurred during task [{type(self)}] execution: {e}")

    async def connect(self):
        attempt = 1
        self.client = BleakClient(self.device.address, disconnected_callback=self.disconnect_handler)

        while self.is_active() and not self.client.is_connected:
            print(f"Attempting to connect to [{self.device.name}:{self.device.address}]. Attempt={attempt}")
            try:
                await self.client.connect()
                print(f"Connected to [{self.device.name}:{self.device.address}]")

            except Exception as e:
                print(f"Unable to connect to device [{self.device.name}:{self.device.address}]: {e}")
                await asyncio.sleep(1)
            attempt += 1

    async def extract_features(self):
        if not self.is_active():
            return

        await self.feature_extractor(self.client, self.device)

    async def subscribe_to_events(self):
        if not self.is_active():
            return

        async for value in self.start():
            if not self.is_active():
                stop_message = (
                    "Signal stop received for task "
                    f"[{self.device.name}:{self.device.address}:{self.device.service.characteristic_uuid}]"
                )
                print(stop_message)
                break

            self.callback(*value)
        await self.stop()

    async def start(self) -> AsyncGenerator[Tuple[BleakGATTCharacteristic, bytearray], None]:
        queue = asyncio.Queue()

        async def on_data(characteristic: BleakGATTCharacteristic, data: bytearray):
            await queue.put((characteristic, data))

        print(f"Subscribing for {self.device.service.characteristic_uuid}, device: {self.device.name}")
        await self.client.start_notify(self.device.service.characteristic_uuid, callback=on_data)
        print(f"Subscribed for {self.device.service.characteristic_uuid}, device: {self.device.name}")

        while True:
            characteristic, data = await queue.get()
            queue.task_done()
            yield self.device, data

    def unsubscribe(self):
        self._is_active = False

    def is_active(self):
        return self._is_active

    async def stop(self):
        await self.client.stop_notify(self.device.service.characteristic_uuid)
        await self.client.disconnect()


class ConnectionService(abc.ABC):
    def __init__(self, pool: QThreadPool, model: Model):
        self.pool = pool
        self.model = model
        self.tasks = []

    def set_device(self, device: Device):
        task = MeasurementReadingTask(
            device,
            feature_extractor=self.process_supported_features,
            event_processor=self.process_measurement,
            disconnect_handler=self.handle_disconnect,
        )
        self.tasks.append(task)
        self.pool.start(task)

    @abc.abstractmethod
    async def process_supported_features(self, client: BleakClient, device: Device):
        ...

    @abc.abstractmethod
    def process_measurement(self, device: Device, data: bytearray):
        ...

    def handle_disconnect(self, client: BleakClient):
        for task in reversed(self.tasks):
            print(f"Device [{task.device.name}:{task.device.address}] disconnected.")
            if task.client == client:
                self.tasks.remove(task)
            break
        else:
            print(f"Received a device disconnected callback for device [{client.address}], but no task was found.")
            return

        if not task.is_active():
            return

        print(f"Reconnecting to device [{task.device.name}:{task.device.address}]")

        async def dummy(*_):
            pass

        task = MeasurementReadingTask(
            task.device,
            feature_extractor=dummy,
            event_processor=self.process_measurement,
            disconnect_handler=self.handle_disconnect,
        )
        self.tasks.append(task)
        self.pool.start(task)

    def stop(self):
        for task in self.tasks:
            task.unsubscribe()


class HrmService(ConnectionService):
    def __init__(self, pool: QThreadPool, model: Model):
        super().__init__(pool, model)

    async def process_supported_features(self, _, device: Device):
        self.model.set_hrm(device)

    def process_measurement(self, device: Device, data: bytearray):
        flag = data[0] & 0x01

        if flag == 0:
            hrm = int.from_bytes(data[1:2], byteorder='little', signed=False)
        else:
            hrm = int.from_bytes(data[1:3], byteorder='little', signed=False)

        event = MeasurementEvent(device=device, measurement=HrmMeasurement(hrm))
        self.model.update_hrm(event)


class CyclingCadenceAndSpeedService(ConnectionService):
    CSC_FEATURE_UUID = "00002a5c-0000-1000-8000-00805f9b34fb"

    def __init__(self, pool: QThreadPool, model: Model):
        super().__init__(pool, model)

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


class PowerService(ConnectionService):
    def __init__(self, pool: QThreadPool, model: Model):
        super().__init__(pool, model)

    async def process_supported_features(self, _, device: Device):
        self.model.set_power(device)

    def process_measurement(self, device: Device, data: bytearray):
        power = int.from_bytes(data[1:], byteorder='little', signed=False)
        event = MeasurementEvent(device=device, measurement=HrmMeasurement(power))
        self.model.update_power(event)

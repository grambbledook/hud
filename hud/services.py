import abc
import asyncio
import os
from collections import defaultdict
from typing import Callable, TypeVar, AsyncGenerator, Tuple, Coroutine, Dict

import yaml
from PySide6.QtCore import QRunnable, QThreadPool
from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic

from hud.model import Model, Device, MeasurementEvent, SpeedMeasurement, CadenceMeasurement, HrmMeasurement, \
    SUPPORTED_SERVICES, Service, PowerMeasurement, HRM, PWR, CSC

T = TypeVar('T')


class DeviceRegistry:
    def __init__(self):
        self.clients: Dict[str, BleakClient] = {}
        self.callbacks: Dict[str, list[Callable[[BleakClient], None]]] = defaultdict(list)

    async def connect(self, device: Device, disconnection_callback) -> BleakClient:

        if device.address not in self.clients:
            self.clients[device.address] = BleakClient(device.address, disconnected_callback=self._on_disconnect)

        if disconnection_callback not in self.callbacks[device.address]:
            self.callbacks[device.address].append(disconnection_callback)

        client = self.clients[device.address]

        if not client.is_connected:
            await client.connect()

        return client

    def _on_disconnect(self, client: BleakClient):
        address = client.address
        for callback in self.callbacks[address]:
            callback(client)

    async def stop(self):
        for address, client in self.clients.items():
            print(f"Disconnecting from device [{address}]")

            if client.is_connected:
                await client.disconnect()


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
            registry: DeviceRegistry,
            feature_extractor: Callable[[BleakClient, Device], Coroutine[None, None, None]],
            event_processor: Callable[[Device, bytearray], None],
            disconnect_handler: Callable[[BleakClient], None] = None,
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.device = device
        self.registry = registry
        self.feature_extractor = feature_extractor
        self.callback = event_processor
        self.disconnect_handler = disconnect_handler
        self.client = None

        self._is_active = True
        self._is_closed = False

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
        client, attempt = None, 0

        while self.is_active() and not client:
            attempt += 1

            print(f"Attempting to connect to [{self.device.name}:{self.device.address}]. Attempt={attempt}")
            try:
                client = await self.registry.connect(self.device, self.disconnect_handler)
                print(f"Connected to [{self.device.name}:{self.device.address}]")

            except Exception as e:
                print(f"Unable to connect to device [{self.device.name}:{self.device.address}]: {e}")
                await asyncio.sleep(1)

        self.client = client

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
        await self.clean_up()

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

    def stop(self):
        self.unsubscribe()
        self._is_closed = True

    def is_active(self):
        return self._is_active

    async def clean_up(self):
        await self.client.stop_notify(self.device.service.characteristic_uuid)

        if self._is_closed:
            await self.client.disconnect()


class ConnectionService(abc.ABC):
    def __init__(self, pool: QThreadPool, model: Model, registry: DeviceRegistry):
        self.pool = pool
        self.model = model
        self.registry = registry
        self.tasks = []

    def set_device(self, device: Device):
        task = MeasurementReadingTask(
            device,
            feature_extractor=self.process_supported_features,
            event_processor=self.process_measurement,
            disconnect_handler=self.handle_disconnect,
            registry=self.registry,
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
            registry=self.registry,
        )
        self.tasks.append(task)
        self.pool.start(task)

    def stop(self):
        for task in self.tasks:
            task.stop()


class HrmService(ConnectionService):
    def __init__(self, pool: QThreadPool, model: Model, registry: DeviceRegistry):
        super().__init__(pool, model, registry)

    async def process_supported_features(self, _, device: Device):
        self.model.set_hrm(device)

    def process_measurement(self, device: Device, data: bytearray):
        # GATT Specification Supplement v5: 3.106.2
        flag = data[0]

        if flag & 0x01:
            hrm = int.from_bytes(data[1:3], byteorder='little', signed=False)
        else:
            hrm = int.from_bytes(data[1:2], byteorder='little', signed=False)

        event = MeasurementEvent(device=device, measurement=HrmMeasurement(hrm))
        self.model.update_hrm(event)


class CyclingCadenceAndSpeedService(ConnectionService):
    CSC_FEATURE_UUID = "00002a5c-0000-1000-8000-00805f9b34fb"

    def __init__(self, pool: QThreadPool, model: Model, registry: DeviceRegistry):
        super().__init__(pool, model, registry)

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


class PowerService(ConnectionService):
    def __init__(self, pool: QThreadPool, model: Model, registry: DeviceRegistry):
        super().__init__(pool, model, registry)

    async def process_supported_features(self, _, device: Device):
        self.model.set_power(device)

    def process_measurement(self, device: Device, data: bytearray):
        # GATT Specification Supplement v5: 3.59.2
        power = int.from_bytes(data[2:4], byteorder='little', signed=True)

        event = MeasurementEvent(device=device, measurement=PowerMeasurement(power))
        self.model.update_power(event)


class DataManagementService:
    def __init__(self, model: Model, hr_service: HrmService, csc_service: CyclingCadenceAndSpeedService,
                 power_service: PowerService):
        self.model = model
        self.hr_service = hr_service
        self.csc_service = csc_service
        self.power_service = power_service

    def store(self):
        # Get the user's home directory
        home_dir = os.path.expanduser('~')

        # Define the path to the YAML file
        yaml_file_path = os.path.join(home_dir, '.hud/config.yaml')

        data = {
            "hrm": {
                "device": self.model.hrm.device.name,
                "address": self.model.hrm.device.address,
            } if self.model.hrm.device else None,

            "speed": {
                "device": self.model.speed.device.name,
                "address": self.model.speed.device.address,
            } if self.model.speed.device else None,

            "cadence": {
                "device": self.model.cadence.device.name,
                "address": self.model.cadence.device.address,
            } if self.model.cadence.device else None,

            "power": {
                "device": self.model.power.device.name,
                "address": self.model.power.device.address,
            } if self.model.power.device else None,
        }

        with open(yaml_file_path, "w") as f:
            yaml.dump(data, f)

    def load(self):
        home_dir = os.path.expanduser('~')

        # Define the path to the YAML file
        yaml_file_path = os.path.join(home_dir, '.hud/config.yaml')
        if not os.path.exists(yaml_file_path):
            os.makedirs(os.path.dirname(yaml_file_path), exist_ok=True)
            print("No device data found, using default config.")
            return

        with open(yaml_file_path, "r") as f:
            data = yaml.safe_load(f)

        if data["hrm"]:
            name, address = data["hrm"]["device"], data["hrm"]["address"]
            self.hr_service.set_device(Device(name, address, HRM))

        if data["speed"]:
            name, address = data["speed"]["device"], data["speed"]["address"]
            self.csc_service.set_device(Device(name, address, CSC))

        if data["cadence"]:
            name, address = data["cadence"]["device"], data["cadence"]["address"]
            self.csc_service.set_device(Device(name, address, CSC))

        if data["power"]:
            name, address = data["power"]["device"], data["power"]["address"]
            self.power_service.set_device(Device(name, address, PWR))

    def stop(self):
        pass

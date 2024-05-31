import abc
import asyncio
import random
from typing import Callable, TypeVar, AsyncGenerator, Tuple, Coroutine

from PySide6.QtCore import QRunnable, QThreadPool
from bleak import BleakClient, BleakGATTCharacteristic

from hud.model.data_classes import Device
from hud.model.model import Model
from hud.service.device_registry import DeviceRegistry

T = TypeVar('T')


class MeasurementReadingTask(QRunnable):

    def __init__(
            self,
            device: Device,
            registry: DeviceRegistry,
            feature_extractor: Callable[[BleakClient, Device], Coroutine[None, None, None]],
            event_processor: Callable[[Device, bytearray], None],
            disconnect_handler: Callable[[BleakClient], None] = None,
    ):
        super().__init__()
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


class BaseConnectionService(abc.ABC):
    def __init__(self, pool: QThreadPool, model: Model, registry: DeviceRegistry, mock_mode: bool = False):
        self.pool = pool
        self.model = model
        self.registry = registry
        self.tasks = []
        self.mock_mode = mock_mode

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

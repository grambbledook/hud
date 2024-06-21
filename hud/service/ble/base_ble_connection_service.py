import abc
import asyncio
from abc import ABC
from typing import Callable, TypeVar, AsyncGenerator, Tuple, Coroutine, Any

from hud.model.data_classes import Device, Service
from hud.model.model import Model
from hud.service.ble.ble_client import BleClient
from hud.service.device_registry import DeviceRegistry

T = TypeVar('T')


class Task(abc.ABC):

    @abc.abstractmethod
    async def execute(self):
        ...


class InterruptableTask(Task, ABC):

    def __init__(self):
        self._interrupted: bool = False

    def interrupt(self):
        self._interrupted = True


class SetDeviceTask(Task):
    def __init__(self, client: BleClient,
                 process_feature_and_set_devices: Callable[[BleClient, Device], Coroutine[None, None, None]]):
        self.client: BleClient = client
        self.process_feature_and_set_devices: Callable[
            [BleClient, Device], Coroutine[None, None, None]] = process_feature_and_set_devices

    async def execute(self):
        device = self.client.device
        await self.process_feature_and_set_devices(self.client, device)


class NotificationTask(InterruptableTask):
    def __init__(self, client: BleClient, service: Service, process_measurement: Callable[[Device, bytearray], None]):
        super().__init__()

        self.client: BleClient = client
        self.service: Service = service
        self.process_measurement: Callable[[Device, bytearray], None] = process_measurement

    async def execute(self):
        device = self.client.device

        async for value in self.subscribe(device):
            if self._interrupted:
                await self.unsubscribe()
                break
            self.process_measurement(*value)

    async def unsubscribe(self):
        await self.client.stop_notify(self.service.characteristic_uuid)

    async def subscribe(self, device: Device) -> AsyncGenerator[Tuple[Device, bytearray], None]:
        queue = asyncio.Queue()

        async def on_data(_: Any, data0: bytearray):
            await queue.put((_, data0))

        print(f"Subscribing for {self.service.characteristic_uuid}, device: {device.device_id}")
        await self.client.start_notify(self.service.characteristic_uuid, callback=on_data)
        print(f"Subscribed for {self.service.characteristic_uuid}, device: {device.device_id}")

        while True:
            characteristic, data = await queue.get()
            queue.task_done()
            yield device, data


class BaseConnectionService(abc.ABC):
    def __init__(self, model: Model, registry: DeviceRegistry, service: Service):
        self.model = model
        self.registry = registry
        self.tasks: list[NotificationTask] = []
        self.service = service

    async def set_device(self, device: Device):
        client = await self.registry.connect(device, lambda _: print("Received disconnection callback"))

        set_device_task = SetDeviceTask(client, self.process_feature_and_set_devices)
        await set_device_task.execute()

        self.unsubscribe()
        notify_task = NotificationTask(client, self.service, self.process_measurement)
        self.tasks.append(notify_task)
        await notify_task.execute()

    def unsubscribe(self):
        for task in self.tasks:
            task.interrupt()
        self.tasks = []

    @abc.abstractmethod
    async def process_feature_and_set_devices(self, client: BleClient, device: Device):
        ...

    @abc.abstractmethod
    def process_measurement(self, device: Device, data: bytearray):
        ...

    def stop(self):
        for task in self.tasks:
            task.cancel()

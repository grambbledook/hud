import asyncio
from collections import namedtuple
from typing import Optional
from typing import TypeVar, Generic, AsyncGenerator, Callable

from PyQt5.QtCore import QRunnable
from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic

from hud.listeners import Listeners

Device = namedtuple(
    'DeviceService',
    ['service_uuid', 'characteristic_uuid', 'type', 'transformer']
)

HEART_RATE_MONITOR = Device(
    "0000180d-0000-1000-8000-00805f9b34fb",
    "00002a37-0000-1000-8000-00805f9b34fb",
    "Heart Rate Monitor",
    lambda _, data: data[1],
)

CADENCE_SENSOR = Device(
    "00001816-0000-1000-8000-00805f9b34fb",
    "00002a5b-0000-1000-8000-00805f9b34fb",
    "Cadence Sensor",
    lambda _, data: data[1],
)

SPEED_SENSOR = Device(
    "00001816-0000-1000-8000-00805f9b34fb",
    "00002a5b-0000-1000-8000-00805f9b34fb",
    "Speed Sensor",
    lambda _, data: data[1],
)

POWER_METER = Device(
    "00001818-0000-1000-8000-00805f9b34fb",
    "00002a63-0000-1000-8000-00805f9b34fb",
    "Power Meter",
    lambda _, data: data[1],
)

T = TypeVar('T')


class DeviceHandle(Generic[T]):
    def __init__(self, name: str, client: BleakClient, device: Device):
        self.name: str = name
        self.device: Device = device
        self.client: BleakClient = client

    async def start(self) -> AsyncGenerator[T, None]:
        queue = asyncio.Queue()

        async def on_data(characteristic: BleakGATTCharacteristic, data: bytearray):
            transformed = self.device.transformer(characteristic, data)
            await queue.put(transformed)

        await self.client.connect()
        await self.client.start_notify(self.device.characteristic_uuid, callback=on_data)

        while True:
            value = await queue.get()
            queue.task_done()
            yield value

    async def subscribe(self, callback: Callable[[T], None]):

        async def on_data(characteristic: BleakGATTCharacteristic, data: bytearray):
            print(f"Received data from {self.name}")
            transformed = self.device.transformer(characteristic, data)
            callback(transformed)

        print(f"Connecting to {self.name}")
        await self.client.connect()
        print(f"Subscribing for {self.device.characteristic_uuid}")
        await self.client.start_notify(self.device.characteristic_uuid, callback=on_data)
        print(f"Subscribed for {self.device.characteristic_uuid}")

    async def unsubscribe(self):
        if not self.client:
            return

        await self.client.stop_notify(self.device.characteristic_uuid)
        await self.client.disconnect()


class DeviceScanner(object):
    def __init__(self, device: Device):
        self.device: Device = device

    async def scan(self) -> AsyncGenerator[DeviceHandle, None]:
        scanner = BleakScanner()
        address_to_device_and_advertisement_data = await scanner.discover(return_adv=True)

        for address, (device, advertisement_data) in address_to_device_and_advertisement_data.items():
            if self.device.service_uuid in advertisement_data.service_uuids:
                yield DeviceHandle(
                    name=device.name or address,
                    client=BleakClient(device),
                    device=self.device,
                )


class State(object):
    def __init__(self):
        self.heart_rate: Optional[int] = None
        self.power: Optional[int] = None
        self.cadence: Optional[int] = None
        self.speed: Optional[float] = None


class ScanTask(QRunnable):

    def __init__(self, device: Device, listeners: Listeners, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = device
        self.listeners = listeners
        self.active = True

    def run(self):
        while self.active:
            asyncio.run(self.scan())

    async def scan(self):
        scanner = DeviceScanner(self.device)
        async for device in scanner.scan():
            self.listeners.notify(device)

    def cancel(self):
        self.active = False


class MeasurementReadingTask(QRunnable):

    def __init__(self, device: DeviceHandle[int], callback: Listeners, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = device
        self.hear_rate_received = callback
        self.active = True

    def run(self):
        asyncio.run(self.subscribe())

    async def subscribe(self):
        generator = self.device.start()
        async for value in generator:
            self.hear_rate_received.notify(value)

            if not self.active:
                break

        self.active = False


class StopMeasurementReadingTask(QRunnable):
    def __init__(self, device: DeviceHandle, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = device

    def run(self):
        asyncio.run(self.device.unsubscribe())


class HUDModel(object):
    scan: Optional[ScanTask]

    heart_rate_monitor_task: Optional[MeasurementReadingTask] = None
    cadence_sensor_task: Optional[MeasurementReadingTask] = None
    speed_sensor_task: Optional[MeasurementReadingTask] = None
    power_meter_task: Optional[MeasurementReadingTask] = None

    def __init__(self, pool):
        self.power_meter: Optional[DeviceHandle[int]] = None
        self.heart_rate_monitor: Optional[DeviceHandle[int]] = None
        self.cadence_sensor: Optional[DeviceHandle[int]] = None
        self.speed_sensor: Optional[DeviceHandle[float]] = None

        self.pool = pool

    def start_scan(self, device: Device, device_found: Listeners):
        self.scan = ScanTask(device, device_found)
        self.pool.start(self.scan)

    def stop_scan(self):
        if not self.scan or not self.scan.active:
            return
        self.scan.cancel()

    def update_hrm_device(self, device: DeviceHandle[int]):
        self.heart_rate_monitor = device

    def hrm_unsubscribe(self):
        if not self.heart_rate_monitor_task or not self.heart_rate_monitor_task.active:
            return
        task = StopMeasurementReadingTask(self.heart_rate_monitor)
        self.pool.start(task)

    def hrm_subscribe(self, heart_rate_received: Listeners):
        self.heart_rate_monitor_task = MeasurementReadingTask(self.heart_rate_monitor, heart_rate_received)
        self.pool.start(self.heart_rate_monitor_task)

    def update_cad_device(self, device: DeviceHandle[int]):
        self.cadence_sensor = device

    def cad_unsubscribe(self):
        if not self.cadence_sensor_task or not self.cadence_sensor_task.active:
            return
        task = StopMeasurementReadingTask(self.cadence_sensor)
        self.pool.start(task)

    def cad_subscribe(self, cadence_received: Listeners):
        self.cadence_sensor_task = MeasurementReadingTask(self.cadence_sensor, cadence_received)
        self.pool.start(self.cadence_sensor_task)

    def update_spd_device(self, device: DeviceHandle[float]):
        self.speed_sensor = device

    def spd_unsubscribe(self):
        if not self.speed_sensor_task or not self.speed_sensor_task.active:
            return
        task = StopMeasurementReadingTask(self.speed_sensor)
        self.pool.start(task)

    def spd_subscribe(self, speed_received: Listeners):
        self.speed_sensor_task = MeasurementReadingTask(self.speed_sensor, speed_received)
        self.pool.start(self.speed_sensor_task)

    def update_pwr_device(self, device: DeviceHandle[int]):
        self.power_meter = device

    def pwr_unsubscribe(self):
        if not self.power_meter_task or not self.power_meter_task.active:
            return
        task = StopMeasurementReadingTask(self.power_meter)
        self.pool.start(task)

    def pwr_subscribe(self, power_received: Listeners):
        self.power_meter_task = MeasurementReadingTask(self.power_meter, power_received)
        self.pool.start(self.power_meter_task)


async def run():
    scanner = DeviceScanner(HEART_RATE_MONITOR)
    async for device in scanner.scan():
        i = 0
        await device.subscribe(print)
        await asyncio.sleep(30)
        await device.unsubscribe()


if __name__ == "__main__":
    asyncio.run(run())

import asyncio
from collections import namedtuple
from typing import Optional
from typing import TypeVar, Generic, AsyncGenerator, Callable

from PyQt5.QtCore import QRunnable
from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic

from hud.listeners import Listeners

BleService = namedtuple(
    'DeviceService',
    ['service_uuid', 'characteristic_uuid', 'type', 'transformer']
)
    lambda _, data: data[1],
)


CADENCE_SENSOR = BleService(
    "00001816-0000-1000-8000-00805f9b34fb",
    "00002a5b-0000-1000-8000-00805f9b34fb",
    "Cadence Sensor",
    lambda _, data: data[1]
)

SPEED_SENSOR = BleService(
    "00001816-0000-1000-8000-00805f9b34fb",
    "00002a5b-0000-1000-8000-00805f9b34fb",
    "Speed Sensor",
    lambda _, data: data[1],
)

POWER_METER = BleService(
    "00001818-0000-1000-8000-00805f9b34fb",
    "00002a63-0000-1000-8000-00805f9b34fb",
    "Power Meter",
    lambda _, data: data[1]
)

T = TypeVar('T')


class DeviceHandle(Generic[T]):
    def __init__(self, name: str, client: BleakClient, device: BleService):
        self.name: str = name
        self.device: BleService = device
        self.client: BleakClient = client

    async def start(self) -> AsyncGenerator[T, None]:
        queue = asyncio.Queue()

        async def on_data(characteristic: BleakGATTCharacteristic, data: bytearray):
            await queue.put((characteristic, data))

        await self.client.connect()
        await self.client.start_notify(self.device.characteristic_uuid, callback=on_data)

        while True:
            characteristic, data = await queue.get()
            queue.task_done()
            yield characteristic, data

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
    def __init__(self, device: BleService):
        self.device: BleService = device

    async def scan(self) -> AsyncGenerator[DeviceHandle, None]:
        scanner = BleakScanner()
        address_to_device_and_advertisement_data = await scanner.discover(return_adv=True)

        for address, (device, advertisement_data) in address_to_device_and_advertisement_data.items():
            if self.device.service_uuid in advertisement_data.service_uuids:
                client = BleakClient(device)

                yield DeviceHandle(
                    name=device.name or address,
                    client=BleakClient(device),
                    device=self.device,
                )


class ScanTask(QRunnable):

    def __init__(self, device: BleService, listeners: Listeners, *args, **kwargs):
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


class Model(object):
    heart_rate_monitor: Optional[Device]
    cadence_sensor: Optional[Device]
    speed_sensor: Optional[Device]
    power_meter: Optional[Device]

    hrm = None
    cadence = None

    @classmethod
    def from_yaml(cls, loader, node):
        value = loader.construct_mapping(node)
        return cls(**value)

    def to_yaml(self):
        return {
            'heart_rate_monitor': self.heart_rate_monitor,
            'cadence_sensor': self.cadence_sensor,
            'speed_sensor': self.speed_sensor,
            'power_meter': self.power_meter,
        }

    def __init__(self, heart_rate_monitor=None, cadence_sensor=None, speed_sensor=None, power_meter=None):
        self.heart_rate_monitor = heart_rate_monitor
        self.cadence_sensor = cadence_sensor
        self.speed_sensor = speed_sensor
        self.power_meter = power_meter

    def hrm(self, hrm):
        self.hrm = hrm
        return self.hrm

    def cadence(self, cadence):
        if not self.cadence:
            self.cadence = cadence

        (cur_ccr, cur_lcet), (prev_ccr, prev_lcet), self.cadence = cadence, self.cadence, cadence

        return (cur_ccr - prev_ccr) / (cur_lcet - prev_lcet)

    def speed(self, speed):
        if not self.speed:
            self.speed = speed

        (cur_cwr, cur_lwet), (prev_cwr, prev_lwet), self.speed = speed, self.speed, speed

        return (cur_cwr - prev_cwr) / (cur_lwet - prev_lwet)


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
        self.model = Model()

    def start_scan(self, device: BleService, device_found: Listeners):
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

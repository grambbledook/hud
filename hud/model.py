from typing import Optional

import asyncio
from collections import namedtuple
from typing import TypeVar, Generic, AsyncGenerator, Callable

from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic

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


class HUDModel(object):
    def __init__(self):
        self.power_meter: Optional[DeviceHandle[int]] = None
        self.heart_rate_monitor: Optional[DeviceHandle[int]] = None
        self.cadence_sensor: Optional[DeviceHandle[int]] = None
        self.speed_sensor: Optional[DeviceHandle[float]] = None

        self.state = State()

    def set_heart_rate_monitor(self, device: DeviceHandle[int]):
        self.heart_rate_monitor = device

    def set_cadence_sensor(self, device: DeviceHandle[int]):
        self.cadence_sensor = device

    def set_power_meter(self, device: DeviceHandle[int]):
        self.power_meter = device

    def set_speed_sensor(self, device: DeviceHandle[float]):
        self.speed_sensor = device

    def update_heart_rate(self, heart_rate: int):
        self.state.heart_rate = heart_rate

    def update_speed(self, speed: float):
        self.state.speed = speed

    def update_power(self, power: int):
        self.state.power = power

    def update_cadence(self, cadence: float):
        self.state.cadence = cadence


async def run():
    scanner = DeviceScanner(HEART_RATE_MONITOR)
    async for device in scanner.scan():
        i = 0
        await device.subscribe(print)
        await asyncio.sleep(30)
        await device.unsubscribe()


if __name__ == "__main__":
    asyncio.run(run())

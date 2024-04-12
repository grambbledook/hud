import asyncio
from collections import namedtuple
from time import sleep
from typing import TypeVar, Generic, Callable, Generator, AsyncGenerator

from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic

Device = namedtuple(
    'DeviceService',
    ['service_uuid', 'characteristic_uuid', 'name', 'transformer']
)

HEART_RATE_MONITOR = Device(
    "0000180d-0000-1000-8000-00805f9b34fb",
    "00002a37-0000-1000-8000-00805f9b34fb",
    "Heart Rate Monitor",
    lambda data: data[1],
)

CADENCE_SENSOR = Device(
    "00001816-0000-1000-8000-00805f9b34fb",
    "00002a5b-0000-1000-8000-00805f9b34fb",
    "Cadence Sensor",
    lambda data: data[1],
)

SPEED_SENSOR = Device(
    "00001816-0000-1000-8000-00805f9b34fb",
    "00002a5b-0000-1000-8000-00805f9b34fb",
    "Speed Sensor",
    lambda data: data[1],
)

POWER_METER = Device(
    "00001818-0000-1000-8000-00805f9b34fb",
    "00002a63-0000-1000-8000-00805f9b34fb",
    "Power Meter",
    lambda data: data[1],
)

T = TypeVar('T')


class DeviceHandle(Generic[T]):
    def __init__(self, name: str, client: BleakClient, device: Device):
        self.name: str = name
        self.device: Device = device

        self.client: BleakClient = client

    def subscribe(self, handle: Callable[[T], None], loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()):
        loop.run_until_complete(self.asubscribe(handle))

    async def asubscribe(self, handle: Callable[[T], None]):
        def on_data(characteristic: BleakGATTCharacteristic, data: bytearray) -> None:
            transformed = self.device.transformer(data)
            print(f"Data from {characteristic}: {data}, transformed: {transformed}")
            handle(transformed)

        await self.client.connect()
        await self.client.start_notify(self.device.characteristic_uuid, on_data)

    def unsubscribe(self, loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()):
        loop.run_until_complete(self.aunsubscribe())

    async def aunsubscribe(self):
        if not self.client:
            return

        await self.client.stop_notify(self.device.characteristic_uuid)
        await self.client.disconnect()


class DeviceScanner(object):
    def __init__(self, device: Device):
        self.device: Device = device

    def scan(self, loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()) -> Generator[DeviceHandle, None, None]:
        gen = self.ascan()
        try:
            while True:
                yield loop.run_until_complete(gen.__anext__())
        except StopAsyncIteration:
            pass

    async def ascan(self) -> AsyncGenerator[DeviceHandle, None]:
        scanner = BleakScanner()
        address_to_device_and_advertisement_data = await scanner.discover(return_adv=True)

        for address, (device, advertisement_data) in address_to_device_and_advertisement_data.items():
            if self.device.service_uuid in advertisement_data.service_uuids:
                yield DeviceHandle(
                    name=device.name or address,
                    client=BleakClient(device),
                    device=self.device,
                )


def sync():
    loop = asyncio.new_event_loop()
    scanner = DeviceScanner(HEART_RATE_MONITOR)
    for device in scanner.scan(loop=loop):
        device.subscribe(lambda heart_rate: print(f"Heart rate: {heart_rate}"), loop=loop)
        sleep(10)
        device.unsubscribe(loop=loop)


async def a_sync():
    scanner = DeviceScanner(HEART_RATE_MONITOR)
    async for device in scanner.ascan():
        await device.subscribe(lambda heart_rate: print(f"Heart rate: {heart_rate}"))
        await asyncio.sleep(10)
        await device.unsubscribe()


if __name__ == "__main__":
    print("SYNC__________")
    sync()
    print("ASYNC__________")
    asyncio.run(a_sync())

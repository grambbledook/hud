import asyncio
from collections import namedtuple
from typing import TypeVar, Generic, AsyncGenerator

from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic

from hud.two_way_generator import AsyncBuffer

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

    async def subscribe(self) -> AsyncGenerator[T, None]:
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


async def run():
    scanner = DeviceScanner(HEART_RATE_MONITOR)
    async for device in scanner.scan():
        i = 0
        async for heart_rate in device.subscribe():
            print(f"Heart rate: {heart_rate}")
            i += 1
            if i == 10:
                break
        await device.unsubscribe()


if __name__ == "__main__":
    asyncio.run(run())

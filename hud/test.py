import asyncio
from typing import AsyncGenerator, TypeVar, Generic, Callable

from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic

HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

T = TypeVar('T')


class DeviceHandle(Generic[T]):
    def __init__(self, name: str, client: BleakClient, service_uuid: str, characteristic_uuid: str):
        self.name: str = name
        self.service_uuid: str = service_uuid
        self.characteristic_uuid: str = characteristic_uuid

        self.client: BleakClient = client

    async def subscribe(self, handle: Callable[[T], None]):
        def on_data(characteristic: BleakGATTCharacteristic, data: bytearray) -> None:
            print(f"Data from {characteristic}: {data}")
            handle(data[1])

        await self.client.connect()
        await self.client.start_notify(self.characteristic_uuid, on_data)

    async def unsubscribe(self):
        if not self.client:
            return

        await self.client.stop_notify(self.characteristic_uuid)
        await self.client.disconnect()


class DeviceScanner(object):
    def __init__(self, service_uuid: str, characteristic_uuid: str):
        self.service_uuid = service_uuid
        self.characteristic_uuid = characteristic_uuid

    async def scan(self) -> AsyncGenerator[DeviceHandle, None]:
        scanner = BleakScanner()
        address_to_device_and_advertisement_data = await scanner.discover(return_adv=True)

        for address, (device, advertisement_data) in address_to_device_and_advertisement_data.items():
            if self.service_uuid in advertisement_data.service_uuids:
                yield DeviceHandle(
                    name=device.name or address,
                    service_uuid=self.service_uuid,
                    characteristic_uuid=self.characteristic_uuid,
                    client=BleakClient(device),
                )


async def main():
    scanner = DeviceScanner(HEART_RATE_SERVICE_UUID, HEART_RATE_MEASUREMENT_CHAR_UUID)
    async for device in scanner.scan():
        await device.subscribe(lambda heart_rate: print(f"Heart rate: {heart_rate}"))
        await asyncio.sleep(10)
        await device.unsubscribe()


if __name__ == "__main__":
    asyncio.run(main())

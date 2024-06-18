import asyncio
import random
import traceback
from typing import TypeVar, Generic, Callable, Coroutine, Any

from bleak import BleakClient

from hud.model.data_classes import Device

T = TypeVar('T')


class BleService:
    service_id: str
    characteristics_id: str
    mapper: Callable[[bytearray], T]


async def retry(f, max_retries=5, base_delay=1, max_delay=2.0):
    retries = 0

    for i in range(max_retries):
        try:
            return await f()
        except Exception as e:
            print(f"Exception raised on attempt {i + 1} of {max_retries}.", e)
            traceback.print_exc()
            if i == max_retries - 1:
                raise e

            delay = random.uniform(base_delay, min(max_delay, base_delay * 2 ** retries))
            await asyncio.sleep(delay)


class BleClient(Generic[T]):

    def __init__(self, device: Device, disconnected_callback):
        self.device = device
        self.disconnected_callback = disconnected_callback

        self.delegate = BleakClient(address_or_ble_device=device.address,
                                    disconnected_callback=self._disconnect_callback)

    @property
    def device_id(self):
        return self.device.device_id

    async def is_connected(self):
        return self.delegate.is_connected

    async def connect(self):
        try:
            print(f"Connecting to device='{self.device_id}'...")
            await retry(self.delegate.connect)
            print(f"Connected to device='{self.device_id}'.")
        except Exception as e:
            print(f"Exception raised on connection attempt to device='{self.device_id}'", e)

    async def disconnect(self):
        await self.delegate.disconnect()

    async def start_notify(self, uuid: str, callback: Callable[[Any, bytearray], Coroutine[Any, Any, None]]):
        await self.delegate.start_notify(uuid, callback)

    async def read_gatt_char(self, uuid: str) -> bytearray:
        return await self.delegate.read_gatt_char(uuid)

    async def write(self, uuid: str, payload: bytearray):
        pass

    def _disconnect_callback(self, _: BleakClient):
        async def callback():
            await self.disconnected_callback(self)
        asyncio.ensure_future(callback())

    async def stop_notify(self, characteristic_uuid: str):
        await self.delegate.stop_notify(characteristic_uuid)

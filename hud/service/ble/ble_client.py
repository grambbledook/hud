import asyncio
from functools import cache
from typing import AsyncGenerator, TypeVar, Generic, Callable, Tuple

from bleak import BleakClient

T = TypeVar('T')


class BleService:
    service_id: str
    characteristics_id: str
    mapper: Callable[[bytearray], T]


class BleClient(Generic[T]):

    def __init__(self, device_name: str, address: str, disconnected_callback):
        self.subscriptions = []

        self.address = address
        self.device_name = device_name

        self.disconnected_callback = disconnected_callback

        self.delegate = BleakClient(address_or_ble_device=address, disconnected_callback=self._disconnect_callback)

    @property
    def device_id(self):
        return f"{self.device_name}:{self.address}"

    async def is_connected(self):
        return self.delegate.is_connected

    async def connect(self):
        try:
            print(f"Connecting to device='{self.device_id}'...")
            await self.delegate.connect()
            print(f"Connected to device='{self.device_id}'.")
        except Exception as e:
            print(f"Exception raised on connection attempt to device='{self.device_id}'")

    async def subscribe(self, service: BleService) -> AsyncGenerator[Tuple[str, T], None]:
        queue = asyncio.Queue()

        async def on_data(_: object, payload: bytearray):
            await queue.put(payload)

        print(f"Subscribing for service='{service.characteristics_id}', device='{self.device_id}'...")
        await self.delegate.start_notify(service.characteristics_id, callback=on_data)
        print(f"Subscribed for service='{service.characteristics_id}', device='{self.device_id}'.")

        while True:
            data = await queue.get()
            queue.task_done()
            yield self.device_name, service.mapper(data)

    async def write(self, id: str, payload: bytearray):
        pass

    def _disconnect_callback(self, _: BleakClient):
        self.disconnected_callback(self)

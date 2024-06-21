import asyncio
import inspect
from collections import defaultdict
from typing import Callable, Dict

from hud.model.data_classes import Device
from hud.service.ble.ble_client import BleClient


class DeviceRegistry:
    def __init__(self):
        self.clients: Dict[str, BleClient] = {}
        self.callbacks: Dict[str, list[Callable[[BleClient], None]]] = defaultdict(list)

        self.lock = asyncio.Lock()

    async def connect(self, device: Device, disconnection_callback) -> BleClient:
        async with self.lock:
            return await self._connect(device, disconnection_callback)

    async def _connect(self, device, disconnection_callback):
        if device.device_id not in self.clients:
            self.clients[device.device_id] = BleClient(device=device,
                                                       disconnected_callback=self._on_disconnect)

        if disconnection_callback not in self.callbacks[device.device_id]:
            self.callbacks[device.device_id].append(disconnection_callback)

        client = self.clients[device.device_id]

        if not await client.is_connected():
            await client.connect()

        return client

    async def _on_disconnect(self, client: BleClient):
        async with self.lock:
            for callback in self.callbacks[client.device_id]:
                callback(client)

    async def stop(self):
        async with self.lock:
            await self._stop()

    async def _stop(self):
        for device_id, client in self.clients.items():
            print(f"Disconnecting from device [{device_id}]")

            if client.is_connected():
                await client.disconnect()

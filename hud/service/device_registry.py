from collections import defaultdict
from typing import Callable, Dict

from bleak import BleakClient

from hud.model.data_classes import Device


class DeviceRegistry:
    def __init__(self):
        self.clients: Dict[str, BleakClient] = {}
        self.callbacks: Dict[str, list[Callable[[BleakClient], None]]] = defaultdict(list)

    async def connect(self, device: Device, disconnection_callback) -> BleakClient:

        if device.address not in self.clients:
            self.clients[device.address] = BleakClient(device.address, disconnected_callback=self._on_disconnect)

        if disconnection_callback not in self.callbacks[device.address]:
            self.callbacks[device.address].append(disconnection_callback)

        client = self.clients[device.address]

        if not client.is_connected:
            await client.connect()

        return client

    def _on_disconnect(self, client: BleakClient):
        address = client.address
        for callback in self.callbacks[address]:
            callback(client)

    async def stop(self):
        for address, client in self.clients.items():
            print(f"Disconnecting from device [{address}]")

            if client.is_connected:
                await client.disconnect()

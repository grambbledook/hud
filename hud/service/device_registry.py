from collections import defaultdict
from typing import Callable, Dict

from hud.model.data_classes import Device
from hud.service.ble.ble_client import BleClient


class DeviceRegistry:
    def __init__(self):
        self.clients: Dict[str, BleClient] = {}
        self.callbacks: Dict[str, list[Callable[[BleClient], None]]] = defaultdict(list)

    async def connect(self, device: Device, disconnection_callback) -> BleClient:
        device_id = f"{device.name}:{device.address}"
        if device_id not in self.clients:
            self.clients[device_id] = BleClient(device_name=device.name, address=device.address,
                                                disconnected_callback=self._on_disconnect)
        if disconnection_callback not in self.callbacks[device_id]:
            self.callbacks[device_id].append(disconnection_callback)

        client = self.clients[device_id]

        if not client.is_connected():
            await client.connect()

        return client

    def _on_disconnect(self, client: BleClient):
        client.connect()

        for callback in self.callbacks[client.device_id]:
            callback(client)

    async def stop(self):
        for address, client in self.clients.items():
            print(f"Disconnecting from device [{address}]")

            if client.is_connected:
                pass

from typing import Protocol

from hud.model.data_classes import Device


class DeviceController(Protocol):

    async def start_device_scan(self):
        ...

    async def stop_device_scan(self):
        ...

    async def set_device(self, device: Device):
        ...

    def stop(self):
        ...

    def store(self):
        ...

    def load(self):
        ...


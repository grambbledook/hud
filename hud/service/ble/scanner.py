import asyncio
from typing import Callable

from PySide6.QtCore import QRunnable, QThreadPool
from bleak import BleakScanner

from hud.model import Service, SUPPORTED_SERVICES
from hud.model.data_classes import Device
from hud.model.model import Model


class ScanTask(QRunnable):

    def __init__(self, services: list[Service], publish_device: Callable[[Device], None], *args, **kwargs):
        super().__init__()
        self.services = services
        self.publish_device = publish_device

    def run(self):
        asyncio.run(self.scan())

    async def scan(self):
        scanner = BleakScanner()

        for _ in range(5):
            await self._do_scan(scanner)

    async def _do_scan(self, scanner: BleakScanner):
        supported_services = dict(map(lambda s: (s.service_uuid, s), self.services))

        address_to_device_and_advertisement_data = await scanner.discover(return_adv=True)
        for device, advertisement_data in address_to_device_and_advertisement_data.values():
            for service_uuid in set(supported_services) & set(advertisement_data.service_uuids):
                device = Device(device.name, device.address, supported_services[service_uuid])

                self.publish_device(device)


class BleDiscoveryService:

    def __init__(self, pool: QThreadPool, model: Model):
        self.pool = pool
        self.model = model

    def start_scan(self):
        task = ScanTask(SUPPORTED_SERVICES, self._append_device)
        self.pool.start(task)

    def _append_device(self, device: Device):
        if device in self.model.devices:
            return

        self.model.devices.append(device)

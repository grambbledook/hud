import asyncio
from asyncio import Task
from typing import Callable

from bleak import BleakScanner

from hud.model import Service
from hud.model.data_classes import Device
from hud.model.model import Model
from hud.service.ble.base_ble_connection_service import InterruptableTask


class ScanTask(InterruptableTask):
    def __init__(self, services: list[Service], discover_device: Callable[[Device], None]):
        super().__init__()
        self.scanner = BleakScanner()
        self.services = services
        self.discover_device = discover_device

    async def execute(self):
        for i in range(5):
            if self._interrupted:
                break

            print(f"Start scanning. Pass {i + 1}... ")
            total, supported = await self._do_scan(self.services)
            print(f"Scanning finished. Total devices: {total}. Supported devices: {supported}.")

    async def _do_scan(self, services: list[Service]):
        candidate_services = dict(map(lambda s: (s.service_uuid, s), services))
        address_to_device_and_advertisement_data = await self.scanner.discover(return_adv=True)

        supported_devices = 0
        for device, advertisement_data in address_to_device_and_advertisement_data.values():

            services = set(candidate_services) & set(advertisement_data.service_uuids)
            if not services:
                continue

            supported_services = [candidate_services[service_uuid] for service_uuid in services]
            device = Device(device.name, device.address, supported_services=supported_services)
            print(f"Candidate device: {device.device_id}")
            self.discover_device(device)
            supported_devices += 1

        return len(address_to_device_and_advertisement_data), supported_devices


class BleDiscoveryService:

    def __init__(self, services: list[Service], model: Model):
        self.tasks: list[Task] = []
        self.services: list[Service] = services
        self.model: Model = model

    async def start_scan(self):
        await self.stop_scan()

        unit = ScanTask(discover_device=self.append_device, services=self.services)

        task = asyncio.create_task(unit.execute())
        self.tasks.append(task)
        try:
            await task
        except asyncio.CancelledError:
            print("Old scan task was cancelled.")

    async def stop_scan(self):
        for task in self.tasks:
            task.cancel()

        self.tasks.clear()

    def append_device(self, device: Device):
        self.model.add_device(device)

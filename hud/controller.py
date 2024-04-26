from typing import Protocol

from hud import devices
from hud.models import Device, Model
from hud.services import BleDiscoveryService, CyclingCadenceAndSpeedService


class View(Protocol):
    def update_view(self, model: Model):
        ...


class DeviceController:
    def __init__(
            self,
            scan_service: BleDiscoveryService,
            hrm_service: CyclingCadenceAndSpeedService,
            csc_service: CyclingCadenceAndSpeedService,

    ):
        self.scan_service = scan_service
        self.hrm_service = hrm_service
        self.csc_service = csc_service

    def start_scan(self):
        self.scan_service.start_scan()

    def set_device(self, device: Device):
        match device.service:
            case devices.HRM:
                print(f"HRM: {device}")
                self.hrm_service.set_device(device)

            case devices.CSC:
                print(f"CADENCE AND SPEED: {device}")
                self.csc_service.set_device(device)
            case devices.PWR:
                print(f"POWER: {device}")
            case _:
                print(f"Unknown: {device}")

from typing import Protocol

from hud import model
from hud.model import Device, Model
from hud.services import BleDiscoveryService, CyclingCadenceAndSpeedService, HrmService, PowerService


class View(Protocol):
    def update_view(self, model: Model):
        ...


class DeviceController:
    def __init__(
            self,
            scan_service: BleDiscoveryService,
            hrm_service: HrmService,
            csc_service: CyclingCadenceAndSpeedService,
            power_service: PowerService,

    ):
        self.scan_service = scan_service
        self.hrm_service = hrm_service
        self.csc_service = csc_service
        self.power_service = power_service

    def start_scan(self):
        self.scan_service.start_scan()

    def set_device(self, device: Device):
        print(f"Device found: {device}")

        match device.service:
            case model.HRM:
                self.hrm_service.set_device(device)
            case model.CSC:
                self.csc_service.set_device(device)
            case model.PWR:
                self.power_service.set_device(device)
            case _:
                print(f"Unknown: {device}")

    def stop(self):
        print("Stopping HRM Service...")
        self.hrm_service.stop()

        print("Stopping CSC Service...")
        self.csc_service.stop()

        print("Stopping Power Service...")
        self.power_service.stop()
        print("All services stopped.")

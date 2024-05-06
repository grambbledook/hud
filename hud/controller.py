from typing import Protocol

from hud import model
from hud.model import Device, Model
from hud.services import BleDiscoveryService, CyclingCadenceAndSpeedService, HrmService, PowerService, DeviceRegistry, \
    DataManagementService


class View(Protocol):
    def update_view(self, model: Model):
        ...


class DeviceController:
    def __init__(
            self,
            scan_service: BleDiscoveryService,
            hr_service: HrmService,
            csc_service: CyclingCadenceAndSpeedService,
            power_service: PowerService,
            config_service: DataManagementService,

    ):
        self.scan_service = scan_service
        self.hrm_service = hr_service
        self.csc_service = csc_service
        self.power_service = power_service
        self.config_service = config_service

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
        print("Closing connections to Devices...")

        print("Unsubscribing from HRM Service...")
        self.hrm_service.stop()

        print("Unsubscribing from CSC Service...")
        self.csc_service.stop()

        print("Unsubscribing from Power Service...")
        self.power_service.stop()

        print("All services stopped.")

    def store(self):
        print("Storing configuration...")
        self.config_service.store()

    def load(self):
        print("Loading configuration...")
        self.config_service.load()

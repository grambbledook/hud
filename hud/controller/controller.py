from hud import model
from hud.model.data_classes import Device
from hud.service.ble.cycling_speed_cadence_service import CyclingCadenceAndSpeedService
from hud.service.ble.fec_bike_trainer_service import FecBikeTrainerService
from hud.service.ble.heart_rate_service import HeartRateService
from hud.service.ble.power_meter_service import PowerService
from hud.service.ble.scanner import BleDiscoveryService
from hud.service.data_management_service import DataManagementService


class DeviceController:
    def __init__(
            self,
            scan_service: BleDiscoveryService,
            hr_service: HeartRateService,
            csc_service: CyclingCadenceAndSpeedService,
            power_service: PowerService,
            legacy_bike_trainer_service: FecBikeTrainerService,
            config_service: DataManagementService,

    ):
        self.legacy_bike_trainer_service = None
        self.scan_service = scan_service
        self.hrm_service = hr_service
        self.csc_service = csc_service
        self.power_service = power_service
        self.config_service = config_service
        self.legacy_bike_trainer_service = legacy_bike_trainer_service

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
            case model.LEGACY_BIKE_TRAINER:
                self.legacy_bike_trainer_service.set_device(device)
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

        print("All service stopped.")

    def store(self):
        print("Storing configuration...")
        self.config_service.store()

    def load(self):
        print("Loading configuration...")
        self.config_service.load()

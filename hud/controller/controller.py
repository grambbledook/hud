import asyncio

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

    async def start_device_scan(self):
        await self.scan_service.start_scan()

    async def stop_device_scan(self):
        await self.scan_service.stop_scan()

    async def set_device(self, device: Device):
        await self.scan_service.stop_scan()

        print(f"Device found: {device}")
        tasks = [x for service in device.supported_services for x in [self.set_service(device, service)] if
                 service is not None]
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            print(f"Error connecting to service: [{e}] of device[{device.device_id}]", e)

    def set_service(self, device, service):
        match service:
            case model.HRM:
                return self.hrm_service.set_device(device)
            case model.CSC:
                return self.csc_service.set_device(device)
            case model.PWR:
                return self.power_service.set_device(device)
            case model.LEGACY_BIKE_TRAINER:
                return self.legacy_bike_trainer_service.set_device(device)
            case _:
                print(f"Unknown: {device}")

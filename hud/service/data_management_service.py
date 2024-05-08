import os

import yaml

from hud.model import CSC, HRM, PWR
from hud.model.data_classes import Device
from hud.model.model import Model
from hud.service.ble.cycling_speed_cadence_service import CyclingCadenceAndSpeedService
from hud.service.ble.fec_bike_trainer_service import FecBikeTrainerService
from hud.service.ble.heart_rate_service import HeartRateService
from hud.service.ble.power_meter_service import PowerService


class DataManagementService:
    def __init__(self, model: Model, hr_service: HeartRateService, csc_service: CyclingCadenceAndSpeedService,
                 power_service: PowerService, legacy_bike_trainer_service: FecBikeTrainerService):
        self.model = model
        self.hr_service = hr_service
        self.csc_service = csc_service
        self.power_service = power_service
        self.legacy_bike_trainer_service = legacy_bike_trainer_service

    def store(self):
        # Get the user's home directory
        home_dir = os.path.expanduser('~')

        # Define the path to the YAML file
        yaml_file_path = os.path.join(home_dir, '.hud/config.yaml')

        data = {
            "hrm": {
                "device": self.model.hrm.device.name,
                "address": self.model.hrm.device.address,
            } if self.model.hrm.device else None,

            "speed": {
                "device": self.model.speed.device.name,
                "address": self.model.speed.device.address,
            } if self.model.speed.device else None,

            "cadence": {
                "device": self.model.cadence.device.name,
                "address": self.model.cadence.device.address,
            } if self.model.cadence.device else None,

            "power": {
                "device": self.model.power.device.name,
                "address": self.model.power.device.address,
            } if self.model.power.device else None,
        }

        with open(yaml_file_path, "w") as f:
            yaml.dump(data, f)

    def load(self):
        home_dir = os.path.expanduser('~')

        # Define the path to the YAML file
        yaml_file_path = os.path.join(home_dir, '.hud/config.yaml')
        if not os.path.exists(yaml_file_path):
            os.makedirs(os.path.dirname(yaml_file_path), exist_ok=True)
            print("No device data found, using default config.")
            return

        with open(yaml_file_path, "r") as f:
            data = yaml.safe_load(f)

        if data["hrm"]:
            name, address = data["hrm"]["device"], data["hrm"]["address"]
            self.hr_service.set_device(Device(name, address, HRM))

        if data["speed"]:
            name, address = data["speed"]["device"], data["speed"]["address"]
            self.csc_service.set_device(Device(name, address, CSC))

        if data["cadence"]:
            name, address = data["cadence"]["device"], data["cadence"]["address"]
            self.csc_service.set_device(Device(name, address, CSC))

        if data["power"]:
            name, address = data["power"]["device"], data["power"]["address"]
            self.power_service.set_device(Device(name, address, PWR))

    def stop(self):
        pass

from typing import TypeVar

from hud.model.data_classes import Service

T = TypeVar('T')


HRM = Service(
    type="Heart Rate Monitor",
    service_uuid="0000180d-0000-1000-8000-00805f9b34fb",
    characteristic_uuid="00002a37-0000-1000-8000-00805f9b34fb",
)

CSC = Service(
    type="Cadence & Speed Sensor",
    service_uuid="00001816-0000-1000-8000-00805f9b34fb",
    characteristic_uuid="00002a5b-0000-1000-8000-00805f9b34fb",
)

PWR = Service(
    type="Power Meter",
    service_uuid="00001818-0000-1000-8000-00805f9b34fb",
    characteristic_uuid="00002a63-0000-1000-8000-00805f9b34fb",
)

LEGACY_BIKE_TRAINER = Service(
    type="Bike Trainer (FE-C over Bluetooth)",
    service_uuid="6e40fec1-b5a3-f393-e0a9-e50e24dcca9e",
    characteristic_uuid="6e40fec2-b5a3-f393-e0a9-e50e24dcca9e",
)

SUPPORTED_SERVICES = [HRM, CSC, PWR, LEGACY_BIKE_TRAINER]

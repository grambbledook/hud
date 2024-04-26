from dataclasses import dataclass
from typing import Optional

@dataclass
class Feature:
    uuid: str
    name: str
    value: int



@dataclass
class Service:
    type: str
    service_uuid: str
    characteristic_uuid: str


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


@dataclass
class Device:
    name: str
    address: str
    service: Service

SUPPORTED_SERVICES = [HRM, CSC, PWR]

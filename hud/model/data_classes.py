from dataclasses import dataclass


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


@dataclass
class Device:
    name: str
    address: str
    supported_services: list[Service]

    @property
    def device_id(self):
        return f"{self.name}:{self.address}"

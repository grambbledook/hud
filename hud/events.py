from dataclasses import dataclass
from typing import Generic, TypeVar

from hud.models import Device

T = TypeVar('T')


@dataclass
class HrmMeasurement:
    hrm: int


@dataclass
class SpeedMeasurement:
    cwr: int
    lwet: int


@dataclass
class CadenceMeasurement:
    ccr: int
    lcet: int


@dataclass
class PowerMeasurement:
    power: int


@dataclass
class MeasurementEvent(Generic[T]):
    device: Device
    measurement: T

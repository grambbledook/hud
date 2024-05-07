from dataclasses import dataclass
from typing import Generic

from hud.model import T
from hud.model.data_classes import Device


@dataclass
class HrMeasurement:
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

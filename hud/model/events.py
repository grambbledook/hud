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


@dataclass
class FeStateEvent:
    def __init__(self, fe_state, lap_toggle):
        self.fe_state = fe_state
        self.lap_toggle = lap_toggle


@dataclass
class GeneralDataEvent:
    def __init__(self, elapsed_time, distance_traveled, speed, heart_rate, fe_state_event):
        self.elapsed_time = elapsed_time
        self.distance_traveled = distance_traveled
        self.speed = speed
        self.heart_rate = heart_rate
        self.fe_state_event = fe_state_event


@dataclass
class GeneralSettingsEvent:
    def __init__(self, cycle_length, incline, resistance, fe_state_event):
        self.cycle_length = cycle_length
        self.incline = incline
        self.resistance = resistance
        self.fe_state_event = fe_state_event


@dataclass
class SpecificTrainerDataEvent:
    def __init__(self, update_event_count, instantaneous_cadence, fe_state_event, instantaneous_power, accumulated_power):
        self.update_event_count = update_event_count
        self.instantaneous_cadence = instantaneous_cadence
        self.fe_state_event = fe_state_event
        self.instantaneous_power = instantaneous_power
        self.accumulated_power = accumulated_power

from collections import namedtuple
from typing import Optional

from hud.controller import DeviceHandle

class State(object):
    def __init__(self):
        self.heart_rate: Optional[int] = None
        self.power: Optional[int] = None
        self.cadence: Optional[int] = None
        self.speed: Optional[float] = None


class Devices(object):
    def __init__(self):
        self.power_meter: Optional[DeviceHandle[int]] = None
        self.heart_rate_monitor: Optional[DeviceHandle[int]] = None
        self.cadence_sensor: Optional[DeviceHandle[int]] = None
        self.speed_sensor: Optional[DeviceHandle[float]] = None

        self.state = State()

    def set_heart_rate_monitor(self, device: DeviceHandle[int]):
        if self.heart_rate_monitor:
            self.heart_rate_monitor = device.unsubscribe()

        self.heart_rate_monitor = device
        self.heart_rate_monitor.subscribe(self._update_heart_rate)

    def _update_heart_rate(self, heart_rate: int):
        self.state.heart_rate = heart_rate

    def _update_speed(self, speed: float):
        self.state.speed = speed

    def _update_power(self, power: int):
        self.state.power = power

    def _update_cadence(self, cadence: float):
        self.state.cadence = cadence

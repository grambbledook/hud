from dataclasses import dataclass, field
from typing import Callable, TypeVar, Generic, Optional

T = TypeVar('T')


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


class Channel(Generic[T]):
    def __init__(self):
        self.listeners: list[Callable[[T], None]] = []

    def notify(self, data: T):
        for listener in self.listeners:
            listener(data)

    def subscribe(self, listener: Callable[[T], None]):
        self.listeners.append(listener)


@dataclass
class Notifications:
    devices: Channel[str]
    metrics: Channel[object]


@dataclass
class HrmState:
    latest: int


@dataclass
class SpeedState:
    first_cwr: int
    first_lwet: int
    last_cwr: int
    last_lwet: int
    latest: float


@dataclass
class CadenceState:
    first_ccr: int
    first_lcet: int
    last_ccr: int
    last_lcet: int
    latest: float


@dataclass
class PowerState:
    latest: int


@dataclass
class Connection(Generic[T]):
    device: Optional[Device]
    state: T


@dataclass
class Model:
    hrm: Connection[HrmState] = Connection(None, HrmState(0))
    speed: Connection[SpeedState] = Connection(None, SpeedState(0, 0, 0, 0, 0))
    cadence: Connection[CadenceState] = Connection(None, CadenceState(0, 0, 0, 0, 0))
    power: Connection[PowerState] = Connection(None, PowerState(0))

    devices: list[Device] = field(default_factory=list)

    hrm_notifications: Notifications = Notifications(Channel(), Channel())
    spd_notifications: Notifications = Notifications(Channel(), Channel())
    cad_notifications: Notifications = Notifications(Channel(), Channel())
    pwr_notifications: Notifications = Notifications(Channel(), Channel())

    def set_cadence(self, device: Device):
        print("Setting cadence: ", device)
        self.cadence = Connection(device, CadenceState(0, 0, 0, 0, 0))
        self.cad_notifications.devices.notify(device.name)
        self.cad_notifications.metrics.notify(0)

    def set_speed(self, device: Device):
        print("Setting speed: ", device)
        self.speed = Connection(device, SpeedState(0, 0, 0, 0, 0))
        self.spd_notifications.devices.notify(device.name)
        self.spd_notifications.metrics.notify(0)

    def set_power(self, device: Device):
        self.power = Connection(device, PowerState(0))
        self.pwr_notifications.devices.notify(device.name)
        self.pwr_notifications.metrics.notify(0)

    def set_hrm(self, device: Device):
        self.hrm = Connection(device, HrmState(0))
        self.hrm_notifications.devices.notify(device.name)
        self.hrm_notifications.metrics.notify(0)

    def update_cadence(self, event: MeasurementEvent[CadenceMeasurement]):
        if event.device != self.cadence.device:
            return

        new_ccr, new_lcet = event.measurement.ccr, event.measurement.lcet
        last_ccr, last_lcet = self.cadence.state.last_ccr, self.cadence.state.last_lcet

        if new_lcet <= last_lcet:
            return

        cadence = (new_ccr - last_ccr) / (new_lcet - last_lcet) * 60 * 1000

        self.cadence.state = CadenceState(
            first_ccr=last_ccr, first_lcet=last_lcet,
            last_ccr=new_ccr, last_lcet=new_lcet,
            latest=cadence
        )
        self.cad_notifications.metrics.notify(round(cadence))

    def update_speed(self, event: MeasurementEvent[SpeedMeasurement]):
        if event.device != self.speed.device:
            return

        new_cwr, new_lwet = event.measurement.cwr, event.measurement.lwet
        last_cwr, last_lwet = self.speed.state.last_cwr, self.speed.state.last_lwet

        if new_lwet <= last_lwet:
            return

        speed = (new_cwr - last_cwr) / (new_lwet - last_lwet) * 60 * 1000

        self.speed.state = SpeedState(
            first_cwr=last_cwr, first_lwet=last_lwet,
            last_cwr=new_cwr, last_lwet=new_lwet,
            latest=speed
        )
        self.spd_notifications.metrics.notify(round(speed))

    def update_hrm(self, event: MeasurementEvent[HrmMeasurement]):
        if event.device != self.hrm.device:
            return

        self.hrm.state = HrmState(event.measurement.hrm)
        self.hrm_notifications.metrics.notify(event.measurement.hrm)

    def update_power(self, event: MeasurementEvent[PowerMeasurement]):
        if event.device != self.power.device:
            return

        self.power.state = PowerState(event.measurement.power)
        self.pwr_notifications.metrics.notify(event.measurement.power)

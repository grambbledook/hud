from dataclasses import dataclass, field
from typing import Generic, Optional

from hud.coms.channels import Notifications
from hud.model import T, HRM, CSC, PWR, LEGACY_BIKE_TRAINER
from hud.model.data_classes import Device, Service
from hud.model.events import MeasurementEvent, CadenceMeasurement, SpeedMeasurement, PowerMeasurement, HrMeasurement, \
    GeneralDataEvent

# Conversion factor from millimeters to kilometers
MM_TO_KM = 1 / 1_000_000

# Conversion factor from milliseconds to minutes/hours
# According to the Bluetooth specification, lcet/lwet unit is 1/1024 seconds
MS_TO_MIN = 1 / (60 * 1024)
MS_TO_HOUR = 1 / (60 * 60 * 1024)

# Default circumference of the tire in millimeters
DEFAULT_TIRE_CIRCUMFERENCE_MM = 2168

# Circumference of the tire in millimeters
TIRE_CIRCUMFERENCE_MM = {
    "700-35C": 2168,
    "700-38C": 2180,
    "700-40C": 2200,
}


@dataclass
class State(Generic[T]):
    latest: T
    min: T
    max: T
    average: float
    count: int


@dataclass
class HrmState(State[int]):
    latest: int = 0
    min: int = 0
    max: int = 0
    average: float = 0
    count: int = 0


@dataclass
class SpeedState(State[float]):
    first_cwr: int = 0
    first_lwet: int = 0
    last_cwr: int = 0
    last_lwet: int = 0
    latest: float = 0
    min: float = 0
    max: float = 0
    average: float = 0
    count: int = 0


@dataclass
class CadenceState(State[float]):
    first_ccr: int = 0
    first_lcet: int = 0
    last_ccr: int = 0
    last_lcet: int = 0
    latest: int = 0
    min: int = 0
    max: int = 0
    average: float = 0
    count: int = 0


@dataclass
class PowerState(State[int]):
    latest: int = 0
    min: int = 0
    max: int = 0
    average: float = 0
    count: int = 0


@dataclass
class BikeTrainer(State[int]):
    latest: int = 0
    min: int = 0
    max: int = 0
    average: float = 0
    count: int = 0


@dataclass
class Connection(Generic[T]):
    device: Optional[Device]
    state: T


@dataclass
class Model:
    tire_type: str = "700-35C"

    hrm: Connection[HrmState] = field(default_factory=lambda: Connection(None, HrmState()))
    speed: Connection[SpeedState] = field(default_factory=lambda: Connection(None, SpeedState()))
    cadence: Connection[CadenceState] = field(default_factory=lambda: Connection(None, CadenceState()))
    power: Connection[PowerState] = field(default_factory=lambda: Connection(None, PowerState()))
    trainer: Connection[BikeTrainer] = field(default_factory=lambda: Connection(None, BikeTrainer()))

    devices: dict[str, Device] = field(default_factory=dict)

    hrm_notifications: Notifications = field(default_factory=lambda: Notifications())
    spd_notifications: Notifications = field(default_factory=lambda: Notifications())
    cad_notifications: Notifications = field(default_factory=lambda: Notifications())
    pwr_notifications: Notifications = field(default_factory=lambda: Notifications())
    trainer_notifications: Notifications = field(default_factory=lambda: Notifications())

    def add_device(self, device: Device):
        self.devices[device.address] = device
        if HRM in device.supported_services:
            self.hrm_notifications.device_discovered.notify(device)
        if CSC in device.supported_services:
            self.cad_notifications.device_discovered.notify(device)
            self.spd_notifications.device_discovered.notify(device)
        if PWR in device.supported_services:
            self.pwr_notifications.device_discovered.notify(device)
        if LEGACY_BIKE_TRAINER in device.supported_services:
            self.trainer_notifications.device_discovered.notify(device)

    def find_devices(self, service: Service) -> list[Device]:
        return [device for device in self.devices.values() if service in device.supported_services]

    def set_cadence(self, device: Device):
        print("Setting cadence sensor: ", device)
        self.cadence = Connection(device, CadenceState())
        self.cad_notifications.device_selected.notify(device.name)
        self.cad_notifications.metrics.notify(self.cadence.state)
        print("Cadence sensor set: ", self.cadence)

    def set_speed(self, device: Device):
        print("Setting speed sensor: ", device)
        self.speed = Connection(device, SpeedState())
        self.spd_notifications.device_selected.notify(device.name)
        self.spd_notifications.metrics.notify(self.speed.state)
        print("Speed sensor set: ", self.speed)

    def set_power(self, device: Device):
        print("Setting power meter: ", device)
        self.power = Connection(device, PowerState())
        self.pwr_notifications.device_selected.notify(device.name)
        self.pwr_notifications.metrics.notify(self.power.state)
        print("Power meter set: ", self.power)

    def set_hrm(self, device: Device):
        print("Setting Heart Rate monitor: ", device)
        self.hrm = Connection(device, HrmState())
        self.hrm_notifications.device_selected.notify(device.name)
        self.hrm_notifications.metrics.notify(self.hrm.state)
        print("Heart Rate monitor set: ", self.hrm)

    def set_bike_trainer(self, device: Device):
        print("Setting Bike Trainer: ", device)
        self.trainer = Connection(device, BikeTrainer())
        self.trainer_notifications.device_selected.notify(device.name)
        self.trainer_notifications.metrics.notify("Connected to bike trainer")
        print("Bike Trainer set: ", self.trainer)

    def update_cadence(self, event: MeasurementEvent[CadenceMeasurement]):
        if event.device != self.cadence.device:
            return

        new_ccr, new_lcet = event.measurement.ccr, event.measurement.lcet
        last_ccr, last_lcet = self.cadence.state.last_ccr, self.cadence.state.last_lcet

        # If the last lcet is the same as the new lcet, we don't need to update the cadence
        if new_lcet == last_lcet:
            return

        # Handle the case where the lcet has reset
        lcet_reset_correction = 0 if new_lcet > last_lcet else 0x10000

        total_revolutions = new_ccr - last_ccr
        time_delta = new_lcet + lcet_reset_correction - last_lcet

        time_delta_minutes = time_delta * MS_TO_MIN
        cadence = total_revolutions / time_delta_minutes

        state = self.cadence.state

        state.first_ccr, state.first_ccr = last_ccr, last_lcet
        state.last_lcet, state.last_ccr = new_lcet, new_ccr

        state.latest = round(cadence)
        state.min = min(cadence, state.min)
        state.max = max(cadence, state.max)
        state.average = round((state.average * state.count + cadence) // (state.count + 1))
        state.count += 1

        self.cad_notifications.metrics.notify(state)

    def update_speed(self, event: MeasurementEvent[SpeedMeasurement]):
        if event.device != self.speed.device:
            return

        new_cwr, new_lwet = event.measurement.cwr, event.measurement.lwet
        last_cwr, last_lwet = self.speed.state.last_cwr, self.speed.state.last_lwet

        # If the last lwet is the same as the new lwet, we don't need to update the speed
        if new_lwet == last_lwet:
            return

        # Handle the case where the lwet has reset
        lwet_reset_correction = 0 if new_lwet > last_lwet else 0x10000
        total_revolutions = new_cwr - last_cwr
        time_delta = new_lwet + lwet_reset_correction - last_lwet
        tire_circumference = TIRE_CIRCUMFERENCE_MM.get(self.tire_type, DEFAULT_TIRE_CIRCUMFERENCE_MM)

        total_kmh = total_revolutions * tire_circumference * MM_TO_KM
        time_hours = time_delta * MS_TO_HOUR
        speed = round(total_kmh / time_hours, 1)

        state = self.speed.state

        state.first_cwr, state.first_lwet = last_cwr, last_lwet
        state.last_lwet, state.last_cwr = new_lwet, new_cwr

        state.latest = speed
        state.min = min(speed, state.min)
        state.max = max(speed, state.max)
        state.average = round((state.average * state.count + speed) / (state.count + 1), 1)
        state.count += 1

        self.spd_notifications.metrics.notify(state)

    def update_hrm(self, event: MeasurementEvent[HrMeasurement]):
        if event.device != self.hrm.device:
            return

        state = self.hrm.state

        state.latest = event.measurement.hrm
        state.min = min(event.measurement.hrm, state.min)
        state.max = max(event.measurement.hrm, state.max)
        state.average = (state.average * state.count + event.measurement.hrm) // (state.count + 1)
        state.count += 1

        self.hrm_notifications.metrics.notify(state)

    def update_power(self, event: MeasurementEvent[PowerMeasurement]):
        if event.device != self.power.device:
            return

        state = self.power.state

        state.latest = event.measurement.power
        state.min = min(event.measurement.power, state.min)
        state.max = max(event.measurement.power, state.max)
        state.average = (state.average * state.count + event.measurement.power) // (state.count + 1)
        state.count += 1

        self.pwr_notifications.metrics.notify(state)

    def update_general_data(self, event: MeasurementEvent[GeneralDataEvent]):
        e = event.measurement
        print(
            f"General data: time={e.elapsed_time}, distance={e.distance_traveled}, speed={e.speed}, hr={e.heart_rate}, state={e.fe_state_event}")

    def update_general_settings(self, event):
        e = event.measurement
        print(
            f"General settings: cycle_length={e.cycle_length}, incline={e.incline}, resistance={e.resistance}, state={e.fe_state_event}")

    def update_specific_trainer_data(self, event):
        e = event.measurement
        print(
            f"Specific trainer data: update_event_count={e.update_event_count}, cadence={e.instantaneous_cadence}, ipower={e.instantaneous_power}, apower={e.accumulated_power}, state={e.fe_state_event}")

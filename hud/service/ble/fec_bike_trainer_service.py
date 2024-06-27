from PySide6.QtCore import QThreadPool
from bleak import BleakClient

from hud.model import LEGACY_BIKE_TRAINER
from hud.model.data_classes import Device
from hud.model.events import GeneralDataEvent, MeasurementEvent, GeneralSettingsEvent, FeStateEvent, \
    SpecificTrainerDataEvent
from hud.model.model import Model
from hud.service.ble.base_ble_connection_service import BaseConnectionService
from hud.service.device_registry import DeviceRegistry


class FecBikeTrainerService(BaseConnectionService):

    def __init__(self, model: Model, registry: DeviceRegistry):
        super().__init__(model, registry, service=LEGACY_BIKE_TRAINER)

    async def process_feature_and_set_devices(self, client: BleakClient, device: Device):
        self.model.set_bike_trainer(device)

    def process_measurement(self, device: Device, data: bytearray):
        payload_size = data[1]
        message = data[4:4 + payload_size - 1]
        page_type = message[0]
        #
        try:
            if page_type == 16:
                event = self._parse_general_data_page(device, message)
                self.model.update_general_data(event)
            elif page_type == 17:
                event = self._parse_general_settings_page(device, message)
                self.model.update_general_settings(event)
            elif page_type == 25:
                event = self._parse_specific_trainer_data_page(device, message)
                self.model.update_specific_trainer_data(event)
            else:
                return
        except Exception as e:
            print(f"Error processing measurement: {e}")

    @staticmethod
    def _parse_general_data_page(device: Device, message: bytearray):
        # assuming that the equipment type is a bike trainer
        equipment_type = "trainer"

        elapsed_time = message[2] * 0.25
        distance_traveled = message[3]

        speed_raw = int.from_bytes(message[4:6], 'big')
        speed = speed_raw * 0.001 if speed_raw != 0xFFFF else None

        heart_rate = message[6] if message[6] != 0xFF else None

        fe_state = FecBikeTrainerService._parse_fe_state_bit(message[7])

        event = GeneralDataEvent(elapsed_time=elapsed_time, distance_traveled=distance_traveled, speed=speed,
                                 heart_rate=heart_rate, fe_state_event=fe_state)

        return MeasurementEvent(device=device, measurement=event)

    @staticmethod
    def _parse_general_settings_page(device, message):
        cycle_length = message[3]
        incline_value = int.from_bytes(message[4:6], 'big', signed=True)

        incline = incline_value * 0.01
        if incline > 100 or incline < -100 or incline_value == 0x7FFF:
            incline = None

        resistance = message[6] * 0.5

        fe_state = FecBikeTrainerService._parse_fe_state_bit(message[7])

        event = GeneralSettingsEvent(cycle_length=cycle_length, incline=incline, resistance=resistance,
                                     fe_state_event=fe_state)
        return MeasurementEvent(device=device, measurement=event)

    @staticmethod
    def _parse_specific_trainer_data_page(device, message):
        update_event_count = message[1]
        instantaneous_cadence = message[2] if message[2] != 0xFF else None

        # instantaneous power field is 12 bits
        instantaneous_power = int.from_bytes(message[5:7], 'big') >> 4
        if instantaneous_power == 0xFFF:
            instantaneous_power = accumulated_power = None
        else:
            accumulated_power = int.from_bytes(message[3:5], 'big')

        fe_state = FecBikeTrainerService._parse_fe_state_bit(message[7])

        event = SpecificTrainerDataEvent(update_event_count=update_event_count,
                                         instantaneous_cadence=instantaneous_cadence, fe_state_event=fe_state,
                                         instantaneous_power=instantaneous_power, accumulated_power=accumulated_power)
        return MeasurementEvent(device=device, measurement=event)

    @staticmethod
    def _parse_fe_state_bit(fe_state_bit: int) -> FeStateEvent:
        lap_toggle = fe_state_bit & 0x8
        code = fe_state_bit & 0x7

        if code == 1:
            fe_state = "ASLEEP"
        elif code == 2:
            fe_state = "READY"
        elif code == 3:
            fe_state = "IN_USE"
        elif code == 4:
            fe_state = "FINISHED"
        else:
            fe_state = "UNKNOWN"

        return FeStateEvent(fe_state=fe_state, lap_toggle=lap_toggle)

    def set_target_power(self, device: Device, target_power: int):
        pass

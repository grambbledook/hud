from hud.listeners import DeviceChannel
from hud.model import HUDModel, DeviceHandle, HEART_RATE_MONITOR, CADENCE_SENSOR, SPEED_SENSOR, POWER_METER, Device


class Controller:
    def __init__(self,
                 hrm_channel: DeviceChannel,
                 cad_channel: DeviceChannel,
                 spd_channel: DeviceChannel,
                 pwr_channel: DeviceChannel,
                 model: HUDModel,
                 ):
        self.hrm_channel = hrm_channel
        self.hrm_channel.scan_devices.listeners.append(self.start_hrm_scan)
        self.hrm_channel.device_selected.listeners.append(self.set_heart_rate_monitor)

        self.cad_channel = cad_channel
        self.cad_channel.scan_devices.listeners.append(self.start_cad_scan)
        self.cad_channel.device_selected.listeners.append(self.set_cadence_sensor)

        self.spd_channel = spd_channel
        self.spd_channel.scan_devices.listeners.append(self.start_spd_scan)
        self.spd_channel.device_selected.listeners.append(self.set_speed_monitor)

        self.pwr_channel = pwr_channel
        self.pwr_channel.scan_devices.listeners.append(self.start_pwr_scan)
        self.pwr_channel.device_selected.listeners.append(self.set_power_meter)

        self.model = model

    def start_hrm_scan(self, signal: str):
        self._start_scan(signal, HEART_RATE_MONITOR, self.hrm_channel)

    def start_cad_scan(self, signal: str):
        self._start_scan(signal, CADENCE_SENSOR, self.cad_channel)

    def start_spd_scan(self, signal: str):
        self._start_scan(signal, SPEED_SENSOR, self.spd_channel)

    def start_pwr_scan(self, signal: str):
        self._start_scan(signal, POWER_METER, self.pwr_channel)

    def _start_scan(self, signal: str, device: Device, channel: DeviceChannel):
        match signal:
            case "start":
                self.model.start_scan(device, channel.device_found)
            case _:
                self.model.stop_scan()

    def set_heart_rate_monitor(self, device: DeviceHandle[int]):
        self.model.hrm_unsubscribe()
        self.model.update_hrm_device(device)
        self.model.hrm_subscribe(self.hrm_channel.measurement_received)

    def set_cadence_sensor(self, device: DeviceHandle[int]):
        self.model.cad_unsubscribe()
        self.model.update_cad_device(device)
        self.model.cad_subscribe(self.cad_channel.measurement_received)

    def set_speed_monitor(self, device: DeviceHandle[float]):
        self.model.spd_unsubscribe()
        self.model.update_spd_device(device)
        self.model.spd_subscribe(self.spd_channel.measurement_received)

    def set_power_meter(self, device: DeviceHandle[int]):
        self.model.pwr_unsubscribe()
        self.model.update_pwr_device(device)
        self.model.pwr_subscribe(self.pwr_channel.measurement_received)

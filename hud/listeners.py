from typing import Callable, List


class Listeners:
    def __init__(self):
        self.listeners: List[Callable[[object], None]] = []

    def notify(self, data: object):
        for listener in self.listeners:
            listener(data)

    def subscribe(self, listener: Callable[[object], None]):
        self.listeners.append(listener)

    def unsubscribe(self, listener: Callable[[object], None]):
        self.listeners.remove(listener)


class DeviceChannel:
    def __init__(self):
        self.scan_devices = Listeners()
        self.device_found = Listeners()
        self.device_selected = Listeners()
        self.measurement_received = Listeners()

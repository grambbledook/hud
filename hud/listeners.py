from typing import Callable, List


class Channel:
    def __init__(self, listener):
        self.listener = listener
        self._active = True

    def notify(self, data: object):
        self.listener(data)

    def is_active(self):
        return self._active

    def close(self):
        self._active = False


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
        self.device_selected = Listeners()
        self.measurement_received = Listeners()

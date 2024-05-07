from dataclasses import dataclass
from typing import Generic, Callable

from hud.coms import T


class Channel(Generic[T]):
    def __init__(self):
        self.listeners: list[Callable[[T], None]] = []

    def notify(self, data: T):
        for listener in self.listeners:
            listener(data)

    def subscribe(self, listener: Callable[[T], None]):
        self.listeners.append(listener)


@dataclass
class Notifications(Generic[T]):
    devices: Channel[str] = Channel[str]()
    metrics: Channel[T] = Channel[T]()

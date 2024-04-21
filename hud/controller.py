import asyncio
from typing import Callable, Generic, Coroutine, AsyncGenerator

import qasync
from PyQt5.QtCore import QThread, QRunnable, QThreadPool

from hud.model import HUDModel, T, DeviceHandle
from hud.view import HUDView


class TaskPool:
    def __init__(self, update_heartrate, update_cadence, update_power, update_speed):
        self.tasks = {
            "heart_rate_monitor": BLEConnection(update_heartrate),
            "cadence_sensor": BLEConnection(update_cadence),
            "power_meter": BLEConnection(update_power),
            "speed_sensor": BLEConnection(update_speed),
        }

    def stop_all(self):
        for task in self.tasks:
            task.stop()


class Controller:
    def __init__(self, model: HUDModel, view: HUDView):
        self.model = model
        self.view = view
        self.workers = TaskPool(
            self.heart_rate_data_received,
            self.cadence_data_received,
            self.power_data_received,
            self.speed_data_received
        )

        self.view.heart_rate_monitor.device_selected_signal.connect(self.set_heart_rate_monitor)
        # self.view.cadence_sensor.device_selected_signal.connect(
        #     lambda x: self.loop.run_until_complete(self.set_cadence_sensor(x))
        # )
        # self.view.power_meter.device_selected_signal.connect(self.set_power_meter)
        # self.view.speed_sensor.device_selected_signal.connect(self.set_speed_sensor)
        #
        self.view.shutdown_signal.connect(self.shut_down)

    def set_heart_rate_monitor(self, device: DeviceHandle[T]):
        if self.model.heart_rate_monitor:
            print(f"Unsubscribing from device {self.model.heart_rate_monitor.name}")
            task = ControllerTask(self.model.heart_rate_monitor.unsubscribe())
            QThreadPool.globalInstance().start(task)
            print(f"Unsubscribe task started")

        self.model.heart_rate_monitor = device
        print(f"Subscribing to device {self.model.heart_rate_monitor.name}")
        task = ProducerTask(
            self.model.heart_rate_monitor.start(),
            self.heart_rate_data_received
        )

        QThreadPool.globalInstance().start(task)
        print(f"Subscribe task started")

    async def set_cadence_sensor(self, device: DeviceHandle[T]):
        if self.model.cadence_sensor:
            await self.model.cadence_sensor.unsubscribe()

        self.model.set_cadence_sensor(device)
        await device.subscribe(self.cadence_data_received)

    async def set_power_meter(self, device: DeviceHandle[T]):
        if self.model.power_meter:
            await self.model.power_meter.unsubscribe()

        self.model.set_power_meter(device)
        await device.subscribe(self.power_data_received)

    async def set_speed_sensor(self, device: DeviceHandle[T]):
        if self.model.speed_sensor:
            await self.model.speed_sensor.unsubscribe()

        self.model.set_speed_sensor(device)
        await device.subscribe(self.speed_data_received)

    def heart_rate_data_received(self, data: T):
        print(data)
        self.model.update_heart_rate(data)
        self.view.update_heart_rate(self.model.state.heart_rate)

    def cadence_data_received(self, data: T):
        self.model.update_cadence(data)
        self.view.update_cadence(self.model.state.cadence)

    def power_data_received(self, data: T):
        self.model.update_power(data)
        self.view.update_power(self.model.state.power)

    def speed_data_received(self, data: T):
        self.model.update_speed(data)
        self.view.update_speed(self.model.state.speed)

    def shut_down(self):
        if self.model.heart_rate_monitor:
            ControllerTask(self.model.heart_rate_monitor.unsubscribe()).start()

        if self.model.cadence_sensor:
            ControllerTask(self.model.cadence_sensor.unsubscribe()).start()

        if self.model.power_meter:
            ControllerTask(self.model.power_meter.unsubscribe()).start()

        if self.model.speed_sensor:
            ControllerTask(self.model.speed_sensor.unsubscribe()).start()

        self.loop.stop()
        self.loop.close()


class ControllerTask(QRunnable, Generic[T]):
    def __init__(self, callable: Coroutine, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callable = callable

    def run(self):
        loop = qasync.QEventLoop(self)
        asyncio.set_event_loop(loop)

        print("Running callable")
        asyncio.run(self.callable)
        print("Done")

    def processEvents(self):
        pass


class BLEConnection(QThread):
    _provider: Callable[[], AsyncGenerator[T, None]]
    _async_generator: AsyncGenerator[T, None]

    def __init__(self, emitter: Callable[[T], None], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._connected = False
        self._running = True
        self._active = False
        self._is_running = True
        self.emitter = emitter

    def run(self):
        print(f"Running BLEConnection {self._provider}")
        loop = qasync.QEventLoop(self)
        asyncio.set_event_loop(loop)

        print(f"Submitting BLEConnection {self._provider}")
        loop.run_until_complete(self.execute())

    async def execute(self):
        while self._running:
            if not self._active:
                await asyncio.sleep(1)
                continue

            if not self._connected:
                self._async_generator = await self._provider()
                self._connected = True

            async for value in self._async_generator:
                if not self._is_running:
                    break

                self.emitter(value)

    def stop(self):
        self._is_running = False

    def processEvents(self):
        pass


class ProducerTask(QRunnable, Generic[T]):
    def __init__(self, generator: AsyncGenerator[T, None], emitter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_running = True
        self.generator = generator
        self.emitter = emitter

    def run(self):
        print(f"Running ProducerTask {self.generator}")
        print(f"Submitting ProducerTask {self.generator}")
        asyncio.run(self.async_generator_to_signal())

    async def async_generator_to_signal(self):
        async for value in self.generator:
            if not self._is_running:
                break

            self.emitter(value)

    def stop(self):
        self._is_running = False

    def processEvents(self):
        pass

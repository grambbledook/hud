import asyncio
import sys
from typing import Generic, TypeVar, AsyncGenerator

import qasync
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QDialog, QListWidget, \
    QListWidgetItem, QGridLayout

from hud.model import DeviceHandle, DeviceScanner, HEART_RATE_MONITOR, SPEED_SENSOR, CADENCE_SENSOR, POWER_METER, Device

T = TypeVar('T')


class WorkerThread(QThread, Generic[T]):
    def __init__(self, generator: AsyncGenerator[T, None], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_running = True
        self.generator = generator

    def run(self):
        loop = qasync.QEventLoop(self)
        asyncio.set_event_loop(loop)

        loop.run_until_complete(self.async_generator_to_signal())

    async def async_generator_to_signal(self):
        async for value in self.generator:
            self.emit(value)

    def emit(self, value: T):
        pass

    def processEvents(self):
        pass

    def stop(self):
        self._is_running = False


class ScanThread(WorkerThread):
    deviceFound = pyqtSignal(DeviceHandle)

    def __init__(self, generator, *args, **kwargs):
        super().__init__(generator, *args, **kwargs)

    def emit(self, value):
        self.deviceFound.emit(value)


class UpdateMetricsThread(WorkerThread):
    value_updated = pyqtSignal(int)

    def __init__(self, generator, *args, **kwargs):
        super().__init__(generator, *args, **kwargs)

    def emit(self, value):
        self.value_updated.emit(value)


class DeviceDialog(QDialog):
    device_selected = pyqtSignal(DeviceHandle)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.listWidget = QListWidget(self)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.listWidget)
        self.listWidget.itemDoubleClicked.connect(self.select_device)

    def closeEvent(self, event):
        if self.thread:
            self.thread.stop()
        event.accept()

    def show_device(self, device):
        item = QListWidgetItem(device.name)
        item.setData(Qt.UserRole, device)
        self.listWidget.addItem(item)

    def select_device(self, item):
        device = item.data(Qt.UserRole)
        self.device_selected.emit(device)
        self.accept()


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()


class DevicePanel(QMainWindow):
    device_selected_signal = pyqtSignal(DeviceHandle)

    def __init__(self, icon_path: str, device: Device, parent=None):
        super().__init__(parent)
        self.device = device
        self.selectIcon = ClickableLabel(self)
        pixmap = QPixmap(icon_path)
        self.selectIcon.setPixmap(pixmap)
        self.deviceLabel = QLabel("No device selected", self)
        self.metricLabel = QLabel("No metrics available", self)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.selectIcon)
        self.layout.addWidget(self.deviceLabel)
        self.layout.addWidget(self.metricLabel)

        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.selectIcon.clicked.connect(self.show_select_device_dialog)

    def closeEvent(self, event):
        self.disconnect()
        event.accept()

    def show_select_device_dialog(self):
        dialog = DeviceDialog(self)
        dialog.thread = ScanThread(DeviceScanner(HEART_RATE_MONITOR).scan())
        dialog.thread.deviceFound.connect(dialog.show_device)
        dialog.device_selected.connect(self.device_selected)
        # dialog.device_selected.connect(lambda x:  self.device_selected_signal.emit(x))

        dialog.thread.start()
        dialog.exec_()

    def device_selected(self, device: DeviceHandle):
        self.device_selected_signal.emit(device)
        self.deviceLabel.setText(f"Device: {device.name}")

    def update_metrics(self, value):
        self.metricLabel.setText(f"Value: {value}")


class HUDView(QMainWindow):
    shutdown_signal = pyqtSignal()  # Signal to shutdown the application

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout()
        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.heart_rate_monitor = DevicePanel(device=HEART_RATE_MONITOR, icon_path="assets/hrm.png")
        self.layout.addWidget(self.heart_rate_monitor, 0, 0)

        self.cadence_sensor = DevicePanel(device=CADENCE_SENSOR, icon_path="assets/cad.png")
        self.layout.addWidget(self.cadence_sensor, 0, 1)

        self.power_meter = DevicePanel(device=POWER_METER, icon_path="assets/pow.png")
        self.layout.addWidget(self.power_meter, 1, 0)

        self.speed_sensor = DevicePanel(device=SPEED_SENSOR, icon_path="assets/spd.png")
        self.layout.addWidget(self.speed_sensor, 1, 1)

    def update_heart_rate(self, value):
        self.heart_rate_monitor.update_metrics(value)

    def update_cadence(self, value):
        self.cadence_sensor.update_metrics(value)

    def update_power(self, value):
        self.power_meter.update_metrics(value)

    def update_speed(self, value):
        self.speed_sensor.update_metrics(value)

    def closeEvent(self, event):
        self.shutdown_signal.emit()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HUDView()
    window.show()
    sys.exit(app.exec_())

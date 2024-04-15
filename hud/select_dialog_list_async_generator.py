import asyncio
import sys
from collections import namedtuple

import qasync
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QDialog, QListWidget, \
    QListWidgetItem

Stub = namedtuple('Stub', ['name', 'value'])


async def scan():
    for i in range(10):
        yield Stub(f"Device {i}", measurements)
        await asyncio.sleep(1)


async def measurements():
    i = 0
    while True:
        yield i
        i += 1
        await asyncio.sleep(1)


class WorkerThread(QThread):
    def __init__(self, generator, *args, **kwargs):
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

    def emit(self, value):
        pass

    def processEvents(self):
        pass

    def stop(self):
        self._is_running = False


class ScanThread(WorkerThread):
    deviceFound = pyqtSignal(Stub)

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
    device_selected = pyqtSignal(Stub)
    thread: ScanThread = None

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


class MainWindow(QMainWindow):
    update_metrics_thread = None
    thread = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selectButton = QPushButton("Select", self)
        self.deviceLabel = QLabel("No device selected", self)
        self.metricLabel = QLabel("No metrics available", self)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.selectButton)
        self.layout.addWidget(self.deviceLabel)
        self.layout.addWidget(self.metricLabel)

        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.selectButton.clicked.connect(self.show_select_device_dialog)

    def show_select_device_dialog(self):
        dialog = DeviceDialog(self)
        dialog.thread = ScanThread(scan())
        dialog.thread.deviceFound.connect(dialog.show_device)
        dialog.device_selected.connect(self.device_selected)

        dialog.thread.start()
        dialog.exec_()

    def device_selected(self, device):
        if self.update_metrics_thread:
            self.update_metrics_thread.stop()

        self.update_selected_device(device)

    def update_selected_device(self, device: Stub):
        self.deviceLabel.setText(f"Device: {device.name}")
        self.update_metrics_thread = UpdateMetricsThread(device.value())
        self.update_metrics_thread.value_updated.connect(self.update_metrics)
        self.update_metrics_thread.start()

    def update_metrics(self, value):
        self.metricLabel.setText(f"Value: {value}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

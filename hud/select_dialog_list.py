import sys
from collections import namedtuple
from time import sleep

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QDialog, QListWidget, \
    QListWidgetItem

Stub = namedtuple('Stub', ['name', 'value'])


def scan():
    for i in range(10):
        yield Stub(f"Device {i}", measurements())
        sleep(1)


def measurements():
    i = 0
    while True:
        yield i
        i += 1
        sleep(1)


class ScanThread(QThread):
    deviceFound = pyqtSignal(Stub)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._isRunning = True

    def run(self):
        for device in scan():
            if not self._isRunning:
                break
            self.deviceFound.emit(device)

    def stop(self):
        self._isRunning = False


class UpdateMetricsThread(QThread):
    valueUpdated = pyqtSignal(int)

    def __init__(self, device, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = device
        self._isRunning = True

    def run(self):
        for value in self.device.value:
            if not self._isRunning:
                break
            self.valueUpdated.emit(value)

    def stop(self):
        self._isRunning = False


class DeviceDialog(QDialog):
    deviceSelected = pyqtSignal(Stub)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.listWidget = QListWidget(self)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.listWidget)
        self.listWidget.itemDoubleClicked.connect(self.selectDevice)

    def addDevice(self, device):
        item = QListWidgetItem(device.name)
        item.setData(Qt.UserRole, device)
        self.listWidget.addItem(item)

    def selectDevice(self, item):
        device = item.data(Qt.UserRole)
        self.deviceSelected.emit(device)
        self.accept()


class MainWindow(QMainWindow):
    updateMetricsThread = None
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

        self.selectButton.clicked.connect(self.selectDevice)

    def selectDevice(self):
        dialog = DeviceDialog(self)
        dialog.deviceSelected.connect(self.deviceSelected)
        self.thread = ScanThread()
        self.thread.deviceFound.connect(dialog.addDevice)
        self.thread.start()
        dialog.exec_()

    def deviceSelected(self, device):
        if self.thread:
            self.thread.stop()

        if self.updateMetricsThread:
            self.updateMetricsThread.stop()

        self.updateDevice(device)

    def updateDevice(self, device):
        self.deviceLabel.setText(f"Device: {device.name}")
        self.updateMetricsThread = UpdateMetricsThread(device)
        self.updateMetricsThread.valueUpdated.connect(self.updateMetrics)
        self.updateMetricsThread.start()

    def updateMetrics(self, value):
        self.metricLabel.setText(f"Value: {value}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

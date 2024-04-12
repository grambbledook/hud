import asyncio

import qasync
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QMessageBox, \
    QMainWindow, QTextEdit, QGridLayout


class DraggableWindow:
    def __init__(self):
        super().__init__()
        self.moving = False
        self.offset = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.moving = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.moving:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.moving = False


class DeviceInformationWindow(QWidget):
    def __init__(self, device_name):
        super().__init__()

        self.device_name = device_name

        self.layout = QVBoxLayout()

        self.label = QLabel(f"{self.device_name}")
        self.text_edit = QTextEdit()

        self.text_edit.setText(f"Data from {self.device_name}")

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.text_edit)

        self.setLayout(self.layout)


class InfoWindowGroup(QMainWindow, DraggableWindow):
    def __init__(self, devices):
        super().__init__()

        self.setWindowTitle("Device Information")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QGridLayout(self.central_widget)

        self.info_windows = [DeviceInformationWindow(device) for device in devices]

        for i, window in enumerate(self.info_windows):
            self.layout.addWidget(window, i // 2, i % 2)


class DevicePanel(QWidget):
    def __init__(self, device_name):
        super().__init__()

        self.device_name = device_name

        self.layout = QVBoxLayout()

        self.button = QPushButton("Select")
        self.button.clicked.connect(self.select_device)

        self.label = QLabel(self.device_name)

        self.layout.addWidget(self.button)
        self.layout.addWidget(self.label)

        self.setLayout(self.layout)

    def select_device(self):
        self.label.setText(self.device_name)
        info_window = DeviceInformationWindow(self.device_name)
        info_window.show()


class MyApp(QWidget, DraggableWindow):
    def __init__(self):
        super().__init__()

        self.devices = ["Heart Rate Monitor", "Cadence Sensor", "Speed Sensor", "Power Meter"]
        self.device_panels = [DevicePanel(device) for device in self.devices]

        self.layout = QHBoxLayout()
        for panel in self.device_panels:
            self.layout.addWidget(panel)

        self.setLayout(self.layout)

        self.info_window_group = InfoWindowGroup(self.devices)
        self.info_window_group.show()


async def main():
    app = QApplication([])
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        window = MyApp()
        window.show()
        await loop.run_forever()


if __name__ == "__main__":
    asyncio.run(main())

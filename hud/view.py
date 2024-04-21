import sys

from PyQt5.QtCore import pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QBrush
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QDialog, QListWidget, \
    QListWidgetItem, QGridLayout, QSystemTrayIcon, QMenu, QAction, QHBoxLayout

from hud.controller import DeviceChannel
from hud.model import DeviceHandle, HEART_RATE_MONITOR, SPEED_SENSOR, CADENCE_SENSOR, POWER_METER, Device


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, normal_icon_path, highlighted_icon_path, parent=None):
        super().__init__(parent)
        self.normal_icon_path = normal_icon_path
        self.highlighted_icon_path = highlighted_icon_path
        self.setPixmap(QPixmap(self.normal_icon_path))

    def enterEvent(self, event):
        self.setPixmap(QPixmap(self.highlighted_icon_path))

    def leaveEvent(self, event):
        self.setPixmap(QPixmap(self.normal_icon_path))

    def mousePressEvent(self, event):
        self.clicked.emit()


class DeviceDialog(QDialog):
    selectDeviceSignal = pyqtSignal(object)

    def __init__(self, parent=None, channel: DeviceChannel = None):
        super().__init__(parent)
        self.channel = channel

        self.listWidget = QListWidget(self)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.listWidget)
        self.listWidget.itemDoubleClicked.connect(self.selectDevice)
        self.listWidget.setStyleSheet(
            """
                QListWidget {
                    background-color: transparent;
                    color: white;
                }
                QListWidget::item {
                    background-color: #808080;
                }
            """
        )

        self.closeLabel = ClickableLabel("assets/ok.png", "assets/ok_high.png", self)
        self.layout.addWidget(self.closeLabel)
        self.closeLabel.clicked.connect(self.onLabelClicked)

        self.hLayout = QHBoxLayout()
        self.hLayout.addStretch()
        self.hLayout.addWidget(self.closeLabel)
        self.hLayout.addStretch()
        self.layout.addLayout(self.hLayout)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def onLabelClicked(self):
        self.close()

    def closeEvent(self, event):
        self.selectDeviceSignal.emit(None)
        event.accept()

    def showDevice(self, device):
        item = QListWidgetItem(device.name)
        item.setData(Qt.UserRole, device)
        if self.listWidget.findItems(device.name, Qt.MatchExactly):
            return
        self.listWidget.addItem(item)

    def selectDevice(self, item):
        device = item.data(Qt.UserRole)

        self.selectDeviceSignal.emit(device)
        self.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.75)  # Set the opacity
        painter.setBrush(QBrush(QColor(0, 0, 0)))  # Set the color to black
        painter.drawRect(self.rect())


class DevicePanel(QMainWindow):
    channel: DeviceChannel

    def __init__(self, normal_icon_path: str, highlighted_icon_path: str, device: Device, channel: DeviceChannel, parent=None):
        super().__init__(parent)
        self.dialog = None

        self.device = device

        self.selectIcon = ClickableLabel(normal_icon_path, highlighted_icon_path, self)
        self.selectIcon.setToolTip("No device selected")

        self.metricLabel = QLabel("No metrics available", self)
        self.metricLabel.setStyleSheet("color: white")

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.selectIcon)
        self.layout.addWidget(self.metricLabel)

        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.selectIcon.clicked.connect(self.showSelectDeviceDialog)

        self.channel = channel
        self.channel.measurement_received.subscribe(self.updateMetrics)

    def closeEvent(self, event):
        self.disconnect()
        event.accept()

    def showSelectDeviceDialog(self):
        self.dialog = DeviceDialog(self, channel=self.channel)
        self.dialog.selectDeviceSignal.connect(self.deviceSelected)

        self.channel.device_found.subscribe(self.dialog.showDevice)
        self.channel.scan_devices.notify("start")

        self.dialog.exec_()

    def deviceSelected(self, device: DeviceHandle):
        self.channel.scan_devices.notify("stop")
        self.channel.device_found.unsubscribe(self.dialog.showDevice)
        self.dialog = None

        if device is None:
            return

        print(f"Device selected {device.name}")
        self.channel.device_selected.notify(device)

        print(f"Device label updated {device.name}")
        self.selectIcon.setToolTip(device.name)

    def updateMetrics(self, value):
        self.metricLabel.setText(f"Value: {value}")


class HUDView(QMainWindow):
    shutdown_signal = pyqtSignal()

    def __init__(
            self,
            hrm_channel: DeviceChannel,
            cad_channel: DeviceChannel,
            spd_channel: DeviceChannel,
            pwr_channel: DeviceChannel,
            parent=None,
    ):
        super().__init__(parent)

        self.layout = QGridLayout()
        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.heart_rate_monitor = DevicePanel(
            channel=hrm_channel,
            device=HEART_RATE_MONITOR,
            normal_icon_path="assets/hrm2.png",
            highlighted_icon_path="assets/hrm2_high.png",
        )
        self.layout.addWidget(self.heart_rate_monitor, 0, 0)

        self.cadence_sensor = DevicePanel(
            channel=cad_channel,
            device=CADENCE_SENSOR,
            normal_icon_path="assets/cad2.png",
            highlighted_icon_path="assets/cad2_high.png",

        )
        self.layout.addWidget(self.cadence_sensor, 0, 1)

        self.power_meter = DevicePanel(
            channel=pwr_channel,
            device=POWER_METER,
            normal_icon_path="assets/pwr2.png",
            highlighted_icon_path="assets/pwr2_high.png",
        )
        self.layout.addWidget(self.power_meter, 1, 0)

        self.speed_sensor = DevicePanel(
            channel=spd_channel,
            device=SPEED_SENSOR,
            normal_icon_path="assets/spd2.png",
            highlighted_icon_path="assets/spd2_high.png",
        )
        self.layout.addWidget(self.speed_sensor, 1, 1)

        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("assets/hrm2.png"))  # Set your app icon
        self.tray_icon_menu = QMenu(self)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        self.tray_icon_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(self.tray_icon_menu)
        self.tray_icon.show()

        self.m_drag = False
        self.m_DragPosition = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.m_drag:
            self.move(event.globalPos() - self.m_DragPosition)
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.25)  # Set the opacity
        painter.setBrush(QBrush(QColor(0, 0, 0)))  # Set the color to black
        painter.drawRect(self.rect())

    def mouseReleaseEvent(self, event):
        self.m_drag = False

    def update_heart_rate(self, value):
        self.heart_rate_monitor.updateMetrics(value)

    def update_cadence(self, value):
        self.cadence_sensor.updateMetrics(value)

    def update_power(self, value):
        self.power_meter.updateMetrics(value)

    def update_speed(self, value):
        self.speed_sensor.updateMetrics(value)

    def closeEvent(self, event):
        self.shutdown_signal.emit()
        event.accept()

    def quit_app(self):
        self.tray_icon.hide()
        self.shutdown_signal.emit()
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HUDView()
    window.show()
    sys.exit(app.exec_())

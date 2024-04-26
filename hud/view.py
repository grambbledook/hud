from typing import Protocol

from PyQt5.QtCore import pyqtSignal, Qt, QPoint, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QBrush
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QDialog, QListWidget, \
    QListWidgetItem, QGridLayout, QSystemTrayIcon, QMenu, QAction, QHBoxLayout

from hud import devices
from hud.devices import Service
from hud.models import Model, Device


class DeviceController(Protocol):

    def start_scan(self):
        ...

    def set_device(self, device: Device):
        ...


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
    selectedDevice = None
    selectDeviceSignal = pyqtSignal(object)

    def __init__(self, parent=None, ):
        super().__init__(parent)

        self.listWidget = QListWidget(self)
        self.listWidget.itemClicked.connect(self.selectItem)
        self.listWidget.itemDoubleClicked.connect(self.confirmSelection)
        self.listWidget.setStyleSheet(
            """
                QListWidget {
                    background-color: transparent;
                    color: white;
                }
                QListWidget::item {
                    background-color: transparent;
                }
                QListWidget::item:selected {
                    background-color: #808080;
                }
            """
        )

        self.closeLabel = ClickableLabel("assets/ok.png", "assets/ok_high.png", self)
        self.closeLabel.clicked.connect(self.onLabelClicked)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.listWidget)
        self.layout.addWidget(self.closeLabel)

        self.hLayout = QHBoxLayout()
        self.hLayout.addStretch()
        self.hLayout.addWidget(self.closeLabel)
        self.hLayout.addStretch()
        self.layout.addLayout(self.hLayout)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.selectedDevice = None

    def onLabelClicked(self):
        self.selectDeviceSignal.emit(self.selectedDevice)
        self.close()

    def closeEvent(self, event):
        event.accept()

    def showDevice(self, device):
        item = QListWidgetItem(device.name)
        item.setData(Qt.UserRole, device)
        if self.listWidget.findItems(device.name, Qt.MatchExactly):
            return
        self.listWidget.addItem(item)

    def selectItem(self, item):
        self.selectedDevice = item.data(Qt.UserRole)

    def confirmSelection(self, item):
        device = item.data(Qt.UserRole)

        self.selectDeviceSignal.emit(device)
        self.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.75)  # Set the opacity
        painter.setBrush(QBrush(QColor(0, 0, 0)))  # Set the color to black
        painter.drawRect(self.rect())


class DevicePanel(QMainWindow):

    def __init__(
            self,
            normal_icon_path: str,
            highlighted_icon_path: str,
            controller: DeviceController,
            ble_service_type: Service,
            model: Model,
            parent=None
    ):
        super().__init__(parent)
        self.dialog = None

        self.model = model
        self.ble_service_type = ble_service_type
        self.controller = controller

        self.selectIcon = ClickableLabel(normal_icon_path, highlighted_icon_path, self)
        self.selectIcon.setToolTip("No device selected")

        self.metricLabel = QLabel("-/-", self)
        self.metricLabel.setStyleSheet(
            """
                QLabel {
                    color: white;
                    font-weight: bold;
                    font-size: 32px;
                    text-align: center;
                }
            """
        )

        # Create a QHBoxLayout, add the metricLabel to it, and add it to the main layout
        self.layout = QGridLayout()
        self.layout.addWidget(self.selectIcon, 0, 0, 1, 1, Qt.AlignCenter)
        self.layout.addWidget(self.metricLabel, 1, 0, 1, 1, Qt.AlignCenter)

        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.selectIcon.clicked.connect(self.showSelectDeviceDialog)

    def showSelectDeviceDialog(self):
        self.dialog = DeviceDialog(self)
        self.dialog.selectDeviceSignal.connect(self.deviceSelected)

        self.controller.start_scan()
        self.dialog_refresher = QTimer()
        self.dialog_refresher.timeout.connect(self.updateDeviceListOnDialog)
        self.dialog_refresher.start(1000)
        self.dialog.exec_()

    def updateDeviceListOnDialog(self):
        for device in self.model.devices:
            if self.ble_service_type.service_uuid != device.service.service_uuid:
                continue
            self.dialog.showDevice(device)

    def deviceSelected(self, device: Device):
        if self.dialog_refresher:
            self.dialog_refresher.stop()
        self.dialog = None

        if device is None:
            return

        self.controller.set_device(device)

    def updateDevice(self, value):
        self.selectIcon.setToolTip(str(value))

    def updateMetrics(self, value):
        self.metricLabel.setText(str(value))

    def closeEvent(self, event):
        self.disconnect()
        event.accept()


class HUDView(QMainWindow):
    shutdown_signal = pyqtSignal()

    def __init__(
            self,
            controller: DeviceController,
            model: Model,
            parent=None,
    ):
        super().__init__(parent)

        self.controller = controller

        self.layout = QGridLayout()
        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.heart_rate_monitor = DevicePanel(
            model=model,
            ble_service_type=devices.HRM,
            controller=controller,
            normal_icon_path="assets/hrm.png",
            highlighted_icon_path="assets/hrm_high.png",
        )
        self.layout.addWidget(self.heart_rate_monitor, 0, 0)
        model.hrm_notifications.devices.subscribe(self.heart_rate_monitor.updateDevice)
        model.hrm_notifications.metrics.subscribe(self.heart_rate_monitor.updateMetrics)

        self.cadence_sensor = DevicePanel(
            model=model,
            ble_service_type=devices.CSC,
            controller=controller,
            normal_icon_path="assets/cad.png",
            highlighted_icon_path="assets/cad_high.png",

        )
        self.layout.addWidget(self.cadence_sensor, 0, 1)
        model.cad_notifications.devices.subscribe(self.cadence_sensor.updateDevice)
        model.cad_notifications.metrics.subscribe(self.cadence_sensor.updateMetrics)

        self.power_meter = DevicePanel(
            model=model,
            ble_service_type=devices.PWR,
            controller=controller,
            normal_icon_path="assets/pwr.png",
            highlighted_icon_path="assets/pwr_high.png",
        )
        self.layout.addWidget(self.power_meter, 1, 0)
        model.pwr_notifications.devices.subscribe(self.power_meter.updateDevice)
        model.pwr_notifications.metrics.subscribe(self.power_meter.updateMetrics)

        self.speed_sensor = DevicePanel(
            model=model,
            ble_service_type=devices.CSC,
            controller=controller,
            normal_icon_path="assets/spd.png",
            highlighted_icon_path="assets/spd_high.png",
        )
        self.layout.addWidget(self.speed_sensor, 1, 1)
        model.spd_notifications.devices.subscribe(self.speed_sensor.updateDevice)
        model.spd_notifications.metrics.subscribe(self.speed_sensor.updateMetrics)

        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("assets/hrm.png"))  # Set your app icon
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

    def mouseReleaseEvent(self, event):
        self.m_drag = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.25)  # Set the opacity
        painter.setBrush(QBrush(QColor(0, 0, 0)))  # Set the color to black
        painter.drawRect(self.rect())

    def closeEvent(self, event):
        self.shutdown_signal.emit()
        event.accept()

    def quit_app(self):
        self.tray_icon.hide()
        self.shutdown_signal.emit()
        QApplication.quit()

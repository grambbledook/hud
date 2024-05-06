from typing import Protocol

from PySide6.QtCore import Signal, Qt, QPoint, QTimer
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QBrush, QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QDialog, QListWidget, \
    QListWidgetItem, QGridLayout, QSystemTrayIcon, QMenu, QHBoxLayout

from hud.config import Config, Theme, BRIGHT, DARK, AppLayout
from hud.model import Model, Device, Service, HRM, CSC, PWR


class DeviceController(Protocol):

    def start_scan(self):
        ...

    def set_device(self, device: Device):
        ...

    def stop(self):
        ...

    def store(self):
        ...

    def load(self):
        ...


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, normal_icon_path: str, highlighted_icon_path: str, theme: Theme, parent=None):
        super().__init__(parent)
        self.normal_icon_path = normal_icon_path
        self.highlighted_icon_path = highlighted_icon_path
        self.norm = self.compute(self.normal_icon_path, theme)
        self.high = self.compute(self.highlighted_icon_path, theme)
        self.setPixmap(self.norm)

    def enterEvent(self, event):
        self.setPixmap(self.high)

    def leaveEvent(self, event):
        self.setPixmap(self.norm)

    def mousePressEvent(self, event):
        self.clicked.emit()

    def compute(self, icon_path, theme) -> QPixmap:
        pixmap = QPixmap(icon_path)
        image = pixmap.toImage()

        for x in range(image.width()):
            for y in range(image.height()):
                color = QColor.fromRgba(image.pixel(x, y))

                if color.alpha() == 0:
                    continue
                r, g, b = theme.background_colour
                color.setRgb(r ^ 0xFF, g ^ 0xFF, b ^ 0xFF)
                image.setPixel(x, y, color.rgba())
        return QPixmap.fromImage(image)


class DeviceDialog(QDialog):
    selectedDevice = None
    selectDeviceSignal = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = None

        self.selectedDevice = None

        self.listWidget = None
        self.closeLabel = None

        self.layout = None
        self.hLayout = None

    def createUI(self, theme: Theme):
        self.theme = theme

        self.listWidget = QListWidget(self)
        self.listWidget.itemClicked.connect(self.selectItem)
        self.listWidget.itemDoubleClicked.connect(self.confirmSelection)
        self.listWidget.setStyleSheet(self.theme.colour_scheme)

        self.closeLabel = ClickableLabel(
            "assets/ok.png",
            "assets/ok_high.png",
            theme=self.theme,
        )
        self.closeLabel.clicked.connect(self.onLabelClicked)

        self.hLayout = QHBoxLayout()
        self.hLayout.addStretch()
        self.hLayout.addWidget(self.closeLabel)
        self.hLayout.addStretch()

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.listWidget)
        self.layout.addLayout(self.hLayout)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.update()

    def onLabelClicked(self):
        self.selectDeviceSignal.emit(self.selectedDevice)
        self.close()

    def closeEvent(self, event):
        event.accept()

    def showDevice(self, device):
        item = QListWidgetItem(device.name)
        item.setData(Qt.ItemDataRole.UserRole, device)
        if self.listWidget.findItems(device.name, Qt.MatchFlag.MatchExactly):
            return
        self.listWidget.addItem(item)

    def selectItem(self, item):
        self.selectedDevice = item.data(Qt.ItemDataRole.UserRole)

    def confirmSelection(self, item):
        device = item.data(Qt.ItemDataRole.UserRole)

        self.selectDeviceSignal.emit(device)
        self.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.75)  # Set the opacity
        painter.setBrush(QBrush(QColor(*self.theme.background_colour)))
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
        self.app_layout = None
        self.metricLabel = None
        self.selectIcon = None
        self.dialog = None
        self.dialog_refresher = None

        self.layout = None
        self.centralWidget = None

        self.model = model
        self.ble_service_type = ble_service_type
        self.controller = controller
        self.highlighted_icon_path = highlighted_icon_path
        self.normal_icon_path = normal_icon_path

    def createUI(self, app_layout: AppLayout):
        self.app_layout = app_layout

        device_tooltip = self.selectIcon.toolTip() if self.selectIcon else "No device selected"

        if self.app_layout.show_buttons:
            self.selectIcon = ClickableLabel(self.normal_icon_path, self.highlighted_icon_path, self.app_layout.theme)
            self.selectIcon.setToolTip(device_tooltip)
            self.selectIcon.clicked.connect(self.showSelectDeviceDialog)

        self.metricLabel = QLabel("--/--", self)
        self.metricLabel.setStyleSheet(self.app_layout.theme.colour_scheme)
        self.metricLabel.setToolTip(device_tooltip)

        # Create a QHBoxLayout, add the metricLabel to it, and add it to the main layout
        self.layout = QGridLayout()
        self.layout.addWidget(self.selectIcon, 0, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.metricLabel, 1, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)

        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.update()

    def switchLayout(self):
        if self.app_layout.show_buttons:
            self.selectIcon.hide()
        else:
            self.selectIcon.show()

        self.selectIcon.update()

        self.layout.update()
        self.adjustSize()
        self.update()

    def showSelectDeviceDialog(self):
        self.dialog = DeviceDialog(self)
        self.dialog.createUI(self.app_layout.theme)
        self.dialog.selectDeviceSignal.connect(self.deviceSelected)

        self.controller.start_scan()
        self.dialog_refresher = QTimer()
        self.dialog_refresher.timeout.connect(self.updateDeviceListOnDialog)
        self.dialog_refresher.start(400)
        self.dialog.exec()

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

    def bind_to_model(self, channel):
        channel.devices.subscribe(self.updateDevice)
        channel.metrics.subscribe(self.updateMetrics)

    def updateDevice(self, value):
        self.selectIcon.setToolTip(str(value))
        self.metricLabel.setToolTip(str(value))

    def updateMetrics(self, value):
        self.metricLabel.setText(str(value))

    def closeEvent(self, event):
        event.accept()


class HUDView(QMainWindow):
    shutdown_signal = Signal()

    def __init__(
            self,
            app_config: Config,
            controller: DeviceController,
            model: Model,
            parent=None,
    ):
        super().__init__(parent)
        self.model = model
        self.controller = controller

        self.layout = None
        self.centralWidget = None
        self.app_config = app_config

        self.heart_rate_monitor_panel = DevicePanel(
            model=model,
            ble_service_type=HRM,
            controller=controller,
            normal_icon_path="assets/hrm.png",
            highlighted_icon_path="assets/hrm_high.png",
        )
        self.heart_rate_monitor_panel.bind_to_model(model.hrm_notifications)

        self.cadence_sensor_panel = DevicePanel(
            model=model,
            ble_service_type=CSC,
            controller=controller,
            normal_icon_path="assets/cad.png",
            highlighted_icon_path="assets/cad_high.png",
        )
        self.cadence_sensor_panel.bind_to_model(model.cad_notifications)

        self.power_meter_panel = DevicePanel(
            model=model,
            ble_service_type=PWR,
            controller=controller,
            normal_icon_path="assets/pwr.png",
            highlighted_icon_path="assets/pwr_high.png",
        )
        self.power_meter_panel.bind_to_model(model.pwr_notifications)

        self.speed_sensor_panel = DevicePanel(
            model=model,
            ble_service_type=CSC,
            controller=controller,
            normal_icon_path="assets/spd.png",
            highlighted_icon_path="assets/spd_high.png",
        )
        self.speed_sensor_panel.bind_to_model(model.spd_notifications)

        self.createUI(self.app_config.app_layout.theme)

        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("assets/hrm.png"))  # Set your app icon
        self.tray_icon_menu = QMenu(self)

        self.switch_theme = QAction("Switch Theme", self)
        self.switch_theme.triggered.connect(self.switchTheme)

        self.hide_buttons = QAction("Hide Buttons", self)
        self.hide_buttons.triggered.connect(self.toggleHideButtons)

        self.quit_action = QAction("Quit", self)
        self.quit_action.triggered.connect(self.quitApp)

        self.tray_icon_menu.addAction(self.switch_theme)
        self.tray_icon_menu.addAction(self.hide_buttons)
        self.tray_icon_menu.addAction(self.quit_action)
        self.tray_icon.setContextMenu(self.tray_icon_menu)
        self.tray_icon.show()

        self.m_drag = False
        self.m_DragPosition = QPoint()

    def createUI(self, style: Theme):
        self.app_config.theme = style

        self.layout = QGridLayout()
        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.layout.addWidget(self.heart_rate_monitor_panel, 0, 0)
        self.layout.addWidget(self.cadence_sensor_panel, 0, 1)
        self.layout.addWidget(self.power_meter_panel, 1, 0)
        self.layout.addWidget(self.speed_sensor_panel, 1, 1)

        self.heart_rate_monitor_panel.createUI(self.app_config.app_layout)
        self.cadence_sensor_panel.createUI(self.app_config.app_layout)
        self.power_meter_panel.createUI(self.app_config.app_layout)
        self.speed_sensor_panel.createUI(self.app_config.app_layout)

        self.heart_rate_monitor_panel.bind_to_model(self.model.hrm_notifications)
        self.cadence_sensor_panel.bind_to_model(self.model.cad_notifications)
        self.power_meter_panel.bind_to_model(self.model.pwr_notifications)
        self.speed_sensor_panel.bind_to_model(self.model.spd_notifications)

        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.m_drag:
            self.move(event.globalPos() - self.m_DragPosition)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.m_drag = False
        self.update()

    def showEvent(self, event):
        super().showEvent(event)

        if not self.app_config.connect_on_start:
            return
        self.controller.load()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.25)  # Set the opacity
        painter.setBrush(QBrush(QColor(*self.app_config.app_layout.theme.background_colour)))  # Set the color to black
        painter.drawRect(self.rect())

    def closeEvent(self, event):
        self.shutdown_signal.emit()
        event.accept()

    def quitApp(self):
        self.tray_icon.hide()
        self.controller.store()
        self.controller.stop()
        QApplication.quit()

    def switchTheme(self):
        if self.app_config.app_layout.theme == BRIGHT:
            self.app_config.app_layout.theme = DARK
        else:
            self.app_config.app_layout.theme = BRIGHT

        self.heart_rate_monitor_panel.createUI(self.app_config.app_layout)
        self.cadence_sensor_panel.createUI(self.app_config.app_layout)
        self.power_meter_panel.createUI(self.app_config.app_layout)
        self.speed_sensor_panel.createUI(self.app_config.app_layout)

        self.adjustSize()
        self.update()

    def toggleHideButtons(self):
        if self.app_config.app_layout.show_buttons:
            self.hide_buttons.setText("Hide Buttons")
        else:
            self.hide_buttons.setText("Show Buttons")

        self.app_config.app_layout.show_buttons = not self.app_config.app_layout.show_buttons

        self.heart_rate_monitor_panel.switchLayout()
        self.cadence_sensor_panel.switchLayout()
        self.speed_sensor_panel.switchLayout()
        self.power_meter_panel.switchLayout()

        self.update()

from PySide6.QtCore import Signal, Qt, QPoint
from PySide6.QtGui import QIcon, QAction, QPainter, QBrush, QColor
from PySide6.QtWidgets import QMainWindow, QSystemTrayIcon, QMenu, QGridLayout, QWidget, QApplication

from hud.configuration.config import Config, Theme, BRIGHT, DARK
from hud.model import HRM, CSC, PWR
from hud.model.model import Model
from hud.view import DeviceController
from hud.view.device_panel import DevicePanel


class MetricsWindow(QMainWindow):
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
            normal_icon_path=self.app_config.asset("hrm.png"),
            highlighted_icon_path=self.app_config.asset("hrm_high.png"),
            app_config=self.app_config,
        )
        self.heart_rate_monitor_panel.bind_to_model(model.hrm_notifications)

        self.cadence_sensor_panel = DevicePanel(
            model=model,
            ble_service_type=CSC,
            controller=controller,
            normal_icon_path=self.app_config.asset("cad.png"),
            highlighted_icon_path=self.app_config.asset("cad_high.png"),
            app_config=self.app_config,
        )
        self.cadence_sensor_panel.bind_to_model(model.cad_notifications)

        self.power_meter_panel = DevicePanel(
            model=model,
            ble_service_type=PWR,
            controller=controller,
            normal_icon_path=self.app_config.asset("pwr.png"),
            highlighted_icon_path=self.app_config.asset("pwr_high.png"),
            app_config=self.app_config,
        )
        self.power_meter_panel.bind_to_model(model.pwr_notifications)

        self.speed_sensor_panel = DevicePanel(
            model=model,
            ble_service_type=CSC,
            controller=controller,
            normal_icon_path=self.app_config.asset("spd.png"),
            highlighted_icon_path=self.app_config.asset("spd_high.png"),
            app_config=self.app_config,
        )
        self.speed_sensor_panel.bind_to_model(model.spd_notifications)

        self.createUI(self.app_config.hud_layout.theme)

        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.app_config.asset("hrm.png")))  # Set your app icon
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

        self.heart_rate_monitor_panel.createUI()
        self.cadence_sensor_panel.createUI()
        self.power_meter_panel.createUI()
        self.speed_sensor_panel.createUI()

        # self.heart_rate_monitor_panel.bind_to_model(self.model.hrm_notifications)
        # self.cadence_sensor_panel.bind_to_model(self.model.cad_notifications)
        # self.power_meter_panel.bind_to_model(self.model.pwr_notifications)
        # self.speed_sensor_panel.bind_to_model(self.model.spd_notifications)

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
        painter.setBrush(QBrush(QColor(*self.app_config.hud_layout.theme.background_colour)))  # Set the color to black
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
        if self.app_config.hud_layout.theme == BRIGHT:
            self.app_config.hud_layout.theme = DARK
        else:
            self.app_config.hud_layout.theme = BRIGHT

        self.heart_rate_monitor_panel.createUI()
        self.cadence_sensor_panel.createUI()
        self.power_meter_panel.createUI()
        self.speed_sensor_panel.createUI()

        self.adjustSize()
        self.update()

    def toggleHideButtons(self):
        if self.app_config.hud_layout.show_buttons:
            self.hide_buttons.setText("Hide Buttons")
        else:
            self.hide_buttons.setText("Show Buttons")

        self.app_config.hud_layout.show_buttons = not self.app_config.hud_layout.show_buttons

        self.heart_rate_monitor_panel.switchLayout()
        self.cadence_sensor_panel.switchLayout()
        self.speed_sensor_panel.switchLayout()
        self.power_meter_panel.switchLayout()

        self.update()

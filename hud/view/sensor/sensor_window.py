from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QBrush, QColor
from PySide6.QtWidgets import QGridLayout, QWidget

from hud.configuration.config import Config
from hud.model import HRM, CSC, PWR
from hud.model.model import Model
from hud.view import DeviceController
from hud.view.primitives.theme_switch import with_switchable_theme
from hud.view.sensor.sensor_panel import SensorPanel
from hud.view.primitives.clickable_label import ClickableLabel
from hud.view.primitives.draggable_window import AppWindow


@with_switchable_theme
class SensorsWindow(AppWindow):
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

        self.heart_rate_monitor_panel = SensorPanel(
            model=model,
            ble_service_type=HRM,
            controller=controller,
            normal_icon_path=self.app_config.asset("hrm.png"),
            highlighted_icon_path=self.app_config.asset("hrm_high.png"),
            app_config=self.app_config,
        )
        self.heart_rate_monitor_panel.bind_to_model(model.hrm_notifications)

        self.cadence_sensor_panel = SensorPanel(
            model=model,
            ble_service_type=CSC,
            controller=controller,
            normal_icon_path=self.app_config.asset("cad.png"),
            highlighted_icon_path=self.app_config.asset("cad_high.png"),
            app_config=self.app_config,
        )
        self.cadence_sensor_panel.bind_to_model(model.cad_notifications)

        self.power_meter_panel = SensorPanel(
            model=model,
            ble_service_type=PWR,
            controller=controller,
            normal_icon_path=self.app_config.asset("pwr.png"),
            highlighted_icon_path=self.app_config.asset("pwr_high.png"),
            app_config=self.app_config,
        )
        self.power_meter_panel.bind_to_model(model.pwr_notifications)

        self.speed_sensor_panel = SensorPanel(
            model=model,
            ble_service_type=CSC,
            controller=controller,
            normal_icon_path=self.app_config.asset("spd.png"),
            highlighted_icon_path=self.app_config.asset("spd_high.png"),
            app_config=self.app_config,
        )
        self.speed_sensor_panel.bind_to_model(model.spd_notifications)

        self.confirmLabel = ClickableLabel(
            normal_icon_path=self.app_config.asset("ok.png"),
            highlighted_icon_path=self.app_config.asset("ok_high.png"),
            theme=self.app_config.hud_layout.theme,
        )
        self.confirmLabel.clicked.connect(lambda: self.next.emit(4))

        self.layout = QGridLayout()
        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.layout.addWidget(self.heart_rate_monitor_panel, 0, 0)
        self.layout.addWidget(self.cadence_sensor_panel, 0, 1)
        self.layout.addWidget(self.power_meter_panel, 1, 0)
        self.layout.addWidget(self.speed_sensor_panel, 1, 1)
        self.layout.addWidget(self.confirmLabel, 3, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.25)  # Set the opacity
        painter.setBrush(QBrush(QColor(*self.app_config.hud_layout.theme.background_colour)))  # Set the color to black
        painter.drawRect(self.rect())

    def quitApp(self):
        self.controller.store()
        self.controller.stop()

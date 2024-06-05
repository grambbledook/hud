from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow, QLabel, QGridLayout, QWidget

from hud.configuration.config import Config
from hud.model import Service
from hud.model.data_classes import Device
from hud.model.model import Model
from hud.view import DeviceController
from hud.view.device_dialog import DeviceDialog
from hud.view.primitives.clickable_label import ClickableLabel, Label
from hud.view.primitives.theme_switch import with_switchable_theme


@with_switchable_theme
class MetricsPanel(QMainWindow):

    def __init__(
            self,
            icon_path: str,
            controller: DeviceController,
            model: Model,
            app_config: Config,
            parent=None
    ):
        super().__init__(parent)
        self.app_config = app_config
        self.dialog = None
        self.dialog_refresher = None

        self.model = model
        self.controller = controller

        self.icon_path = icon_path

        self.selectIcon = Label(
            icon_path=self.icon_path,
            theme=self.app_config.hud_layout.theme,
        )
        self.selectIcon.setToolTip("No device selected")

        self.metricLabel = QLabel("--/--", self)
        self.metricLabel.setStyleSheet(self.app_config.hud_layout.theme.colour_scheme)
        self.metricLabel.setToolTip("No device selected")

        self.layout = QGridLayout()
        self.layout.addWidget(self.selectIcon, 0, 0, 1, 1, Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(self.metricLabel, 0, 1, 1, 1, Qt.AlignmentFlag.AlignLeft)

        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

    def updateDevice(self, value):
        self.selectIcon.setToolTip(str(value))
        self.metricLabel.setToolTip(str(value))

    def updateMetrics(self, value):
        self.metricLabel.setText(str(value.latest))

    def closeEvent(self, event):
        event.accept()

    def bind_to_model(self, channel):
        channel.device_selected.subscribe(self.updateDevice)
        channel.metrics.subscribe(self.updateMetrics)

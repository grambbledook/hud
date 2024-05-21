from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow, QLabel, QGridLayout, QWidget

from hud.configuration.config import Config
from hud.model import Service
from hud.model.data_classes import Device
from hud.model.model import Model
from hud.view import DeviceController
from hud.view.device_dialog import DeviceDialog
from hud.view.primitives.clickable_label import ClickableLabel
from hud.view.primitives.theme_switch import with_switchable_theme


@with_switchable_theme
class SensorPanel(QMainWindow):

    def __init__(
            self,
            normal_icon_path: str,
            highlighted_icon_path: str,
            controller: DeviceController,
            ble_service_type: Service,
            model: Model,
            app_config: Config,
            parent=None
    ):
        super().__init__(parent)
        self.app_config = app_config
        self.dialog = None
        self.dialog_refresher = None

        self.model = model
        self.ble_service_type = ble_service_type
        self.controller = controller
        self.highlighted_icon_path = highlighted_icon_path
        self.normal_icon_path = normal_icon_path

        self.selectIcon = ClickableLabel(
            normal_icon_path=self.normal_icon_path,
            highlighted_icon_path=self.highlighted_icon_path,
            theme=self.app_config.hud_layout.theme,
        )
        self.selectIcon.setToolTip("No device selected")
        self.selectIcon.clicked.connect(self.showSelectDeviceDialog)

        self.metricLabel = QLabel("--/--", self)
        self.metricLabel.setStyleSheet(self.app_config.hud_layout.theme.colour_scheme)
        self.metricLabel.setToolTip("No device selected")

        self.layout = QGridLayout()
        self.layout.addWidget(self.selectIcon, 0, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.metricLabel, 1, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)

        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

    def showSelectDeviceDialog(self):
        self.dialog = DeviceDialog(self.app_config, self)
        self.dialog.selectDeviceSignal.connect(self.deviceSelected)

        self.controller.start_scan()

        # This is a workaround to update the device list on the dialog
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

    def updateDevice(self, value):
        self.selectIcon.setToolTip(str(value))
        self.metricLabel.setToolTip(str(value))

    def updateMetrics(self, value):
        self.metricLabel.setText(str(value.latest))

    def closeEvent(self, event):
        event.accept()

    def bind_to_model(self, channel):
        channel.devices.subscribe(self.updateDevice)
        channel.metrics.subscribe(self.updateMetrics)

import asyncio
from typing import Union

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QLabel, QGridLayout, QWidget

from hud.configuration.config import Config
from hud.model import Service
from hud.model.data_classes import Device
from hud.model.model import Model
from hud.view import DeviceController
from hud.view.device_dialog import DeviceDialog
from hud.view.primitives.clickable_label import ClickableLabel, LabelType
from hud.view.primitives.theme_switch import with_switchable_theme


@with_switchable_theme
class SelectDevicePanel(QMainWindow):

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

        self.model = model
        self.ble_service_type = ble_service_type
        self.controller = controller
        self.highlighted_icon_path = highlighted_icon_path
        self.normal_icon_path = normal_icon_path

        self.selectIcon = ClickableLabel(
            normal_icon_path=self.normal_icon_path,
            highlighted_icon_path=self.highlighted_icon_path,
            theme=self.app_config.hud_layout.theme,
            label_size=LabelType.CLICKABLE_LABEL,
        )
        self.selectIcon.setToolTip("No device selected")
        self.selectIcon.clicked.connect(lambda: asyncio.ensure_future(self.showSelectDeviceDialog()))

        self.metricLabel = QLabel("--/--", self)
        self.metricLabel.setStyleSheet(self.app_config.hud_layout.theme.colour_scheme)
        self.metricLabel.setToolTip("No device selected")

        self.layout = QGridLayout()
        self.layout.addWidget(self.selectIcon, 0, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.metricLabel, 1, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)

        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

    async def showSelectDeviceDialog(self):
        self.dialog = DeviceDialog(self.app_config, self)
        self.dialog.selectDeviceSignal.connect(lambda x: asyncio.ensure_future(self.deviceSelected(x)))
        self.populate_device_list(self.model.find_devices(self.ble_service_type))

        asyncio.ensure_future(self.controller.start_device_scan())
        asyncio.ensure_future(self.dialog.show_async())

    def populate_device_list(self, devices: Union[Device, list[Device]]):
        if not self.dialog:
            return

        data = [devices] if isinstance(devices, Device) else devices

        for device in data:
            self.dialog.showDevice(device)

    async def deviceSelected(self, device: Device):
        self.dialog = None
        self.controller.stop_device_scan()

        if device is None:
            return

        asyncio.ensure_future(self.controller.set_device(device))

    def updateDevice(self, value):
        self.selectIcon.setToolTip(str(value))
        self.metricLabel.setToolTip(str(value))

    def updateMetrics(self, value):
        data = str(value.latest) if hasattr(value, "latest") else "ok"
        self.metricLabel.setText(data)

    def closeEvent(self, event):
        event.accept()

    def bind_to_model(self, channel):
        channel.device_selected.subscribe(self.updateDevice)
        channel.metrics.subscribe(self.updateMetrics)
        channel.device_discovered.subscribe(self.populate_device_list)

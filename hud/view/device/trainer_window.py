from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QBrush, QColor
from PySide6.QtWidgets import QGridLayout, QWidget

from hud.configuration.config import Config
from hud.model import LEGACY_BIKE_TRAINER
from hud.model.model import Model
from hud.view import DeviceController
from hud.view.app_state import AppState
from hud.view.primitives.clickable_label import ClickableLabel
from hud.view.primitives.draggable_window import AppWindow
from hud.view.primitives.theme_switch import with_switchable_theme
from hud.view.device.select_device_panel import SelectDevicePanel


@with_switchable_theme
class TrainerWindow(AppWindow):
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

        self.trainer_panel = SelectDevicePanel(
            normal_icon_path=self.app_config.asset("train.png"),
            highlighted_icon_path=self.app_config.asset("train_high.png"),
            ble_service_type=LEGACY_BIKE_TRAINER,
            model=model,
            controller=controller,
            app_config=self.app_config,
            parent=self,
        )
        self.trainer_panel.bind_to_model(model.trainer_notifications)

        self.confirmLabel = ClickableLabel(
            normal_icon_path=self.app_config.asset("next.png"),
            highlighted_icon_path=self.app_config.asset("next_high.png"),
            theme=self.app_config.hud_layout.theme,
        )
        self.confirmLabel.clicked.connect(lambda: self.next.emit(AppState.WAITING_FOR_SENSORS.value))

        self.layout = QGridLayout()
        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.layout.addWidget(self.trainer_panel, 0, 0)
        self.layout.addWidget(self.confirmLabel, 1, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)

        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.25)  # Set the opacity
        painter.setBrush(QBrush(QColor(*self.app_config.hud_layout.theme.background_colour)))  # Set the color to black
        painter.drawRect(self.rect())

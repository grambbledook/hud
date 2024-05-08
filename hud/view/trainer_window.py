from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPainter, QBrush, QColor
from PySide6.QtWidgets import QGridLayout, QWidget

from hud.configuration.config import Config
from hud.model import LEGACY_BIKE_TRAINER
from hud.model.model import Model
from hud.view import DeviceController
from hud.view.primitives.draggable_window import DraggableWindow
from hud.view.trainer_panel import TrainerPanel


class TrainerWindow(DraggableWindow):
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

        self.heart_rate_monitor_panel = TrainerPanel(
            model=model,
            ble_service_type=LEGACY_BIKE_TRAINER,
            controller=controller,
            app_config=self.app_config,
        )
        self.heart_rate_monitor_panel.bind_to_model(model.hrm_notifications)

        self.layout = QGridLayout()
        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.layout.addWidget(self.heart_rate_monitor_panel, 0, 0)

        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def applyUiChanges(self):
        self.heart_rate_monitor_panel.applyUiChanges()

        self.centralWidget.adjustSize()
        self.adjustSize()
        self.update()

    def switchTheme(self):
        self.applyUiChanges()

    def toggleHideButtons(self):
        print("Toggling buttons")

        self.applyUiChanges()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.25)  # Set the opacity
        painter.setBrush(QBrush(QColor(*self.app_config.hud_layout.theme.background_colour)))  # Set the color to black
        painter.drawRect(self.rect())

    def closeEvent(self, event):
        self.shutdown_signal.emit()
        event.accept()

    def quitApp(self):
        print("Trainer window shut down")

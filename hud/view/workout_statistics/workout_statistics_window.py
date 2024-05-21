from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QBrush, QColor
from PySide6.QtWidgets import QGridLayout, QWidget

from hud.configuration.config import Config
from hud.model import HRM, CSC, PWR
from hud.model.model import Model
from hud.view import DeviceController
from hud.view.sensor.sensor_panel import SensorPanel
from hud.view.primitives.clickable_label import ClickableLabel
from hud.view.primitives.draggable_window import AppWindow
from hud.view.workout.metrics_panel import MetricsPanel


class WorkoutStatisticsWindow(AppWindow):
    def __init__(self, app_config: Config, parent=None):
        super().__init__(parent)

        self.app_config = app_config

        self.newWorkoutLabel = ClickableLabel(
            normal_icon_path=self.app_config.asset("new_workout.png"),
            highlighted_icon_path=self.app_config.asset("new_workout_high.png"),
            theme=self.app_config.hud_layout.theme,
        )
        self.newWorkoutLabel.clicked.connect(lambda: self.next.emit(4))

        self.finishLabel = ClickableLabel(
            normal_icon_path=self.app_config.asset("finish.png"),
            highlighted_icon_path=self.app_config.asset("finish_high.png"),
            theme=self.app_config.hud_layout.theme,
        )
        self.finishLabel.clicked.connect(lambda: self.next.emit(9))

        self.layout = QGridLayout()
        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(self.layout)
        self.setCentralWidget(self.centralWidget)

        self.layout.addWidget(self.newWorkoutLabel, 0, 0, Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.finishLabel, 0, 1, Qt.AlignmentFlag.AlignCenter)

        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.25)  # Set the opacity
        painter.setBrush(QBrush(QColor(*self.app_config.hud_layout.theme.background_colour)))  # Set the color to black
        painter.drawRect(self.rect())

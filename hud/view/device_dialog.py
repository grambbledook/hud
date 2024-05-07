from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPainter, QBrush, QColor
from PySide6.QtWidgets import QDialog, QListWidget, QHBoxLayout, QVBoxLayout, QListWidgetItem

from hud.configuration.config import Config
from hud.view.primitives.clickable_label import ClickableLabel


class DeviceDialog(QDialog):
    selectedDevice = None
    selectDeviceSignal = Signal(object)

    def __init__(self, app_config: Config, parent=None):
        super().__init__(parent)
        self.app_config = app_config

        self.selectedDevice = None

        self.listWidget = None
        self.closeLabel = None

        self.layout = None
        self.hLayout = None

    def createUI(self):
        self.listWidget = QListWidget(self)
        self.listWidget.itemClicked.connect(self.selectItem)
        self.listWidget.itemDoubleClicked.connect(self.confirmSelection)
        self.listWidget.setStyleSheet(self.app_config.hud_layout.theme.colour_scheme)

        self.closeLabel = ClickableLabel(
            normal_icon_path=self.app_config.asset("ok.png"),
            highlighted_icon_path=self.app_config.asset("ok_high.png"),
            theme=self.app_config.hud_layout.theme,
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
        painter.setBrush(QBrush(QColor(*self.app_config.hud_layout.theme.background_colour)))
        painter.drawRect(self.rect())

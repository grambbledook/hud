from enum import Enum

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QMainWindow

from hud.configuration.config import Config
from hud.view.app_state import AppState


class DraggableWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_drag = False
        self.m_DragPosition = QPoint()

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


class AppWindow(DraggableWindow):
    next = Signal(Enum)

    def __init__(self, parent=None):
        super().__init__(parent)

    def applyUiChanges(self, app_config: Config):
        pass

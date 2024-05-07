from PySide6.QtCore import Signal
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import QLabel

from hud.configuration.config import Theme


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, normal_icon_path: str, highlighted_icon_path: str, theme: Theme, parent=None):
        super().__init__(parent)
        self.normal_icon_path = normal_icon_path
        self.highlighted_icon_path = highlighted_icon_path
        self.norm = self.compute(self.normal_icon_path, theme)
        self.high = self.compute(self.highlighted_icon_path, theme)
        self.setPixmap(self.norm)

    def enterEvent(self, event):
        self.setPixmap(self.high)

    def leaveEvent(self, event):
        self.setPixmap(self.norm)

    def mousePressEvent(self, event):
        self.clicked.emit()

    def compute(self, icon_path, theme) -> QPixmap:
        pixmap = QPixmap(icon_path)
        image = pixmap.toImage()

        for x in range(image.width()):
            for y in range(image.height()):
                color = QColor.fromRgba(image.pixel(x, y))

                if color.alpha() == 0:
                    continue
                r, g, b = theme.background_colour
                color.setRgb(r ^ 0xFF, g ^ 0xFF, b ^ 0xFF)
                image.setPixel(x, y, color.rgba())
        return QPixmap.fromImage(image)

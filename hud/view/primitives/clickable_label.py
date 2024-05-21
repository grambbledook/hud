from PySide6.QtCore import Signal
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import QLabel

from hud.configuration.config import Theme


def compute_pixmap(icon_path, theme) -> QPixmap:
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


class Label(QLabel):

    def __init__(self, icon_path: str, theme: Theme, parent=None):
        super().__init__(parent)
        self.norm = None

        self.icon_path = icon_path

        self.applyTheme(theme)

    def applyTheme(self, theme: Theme):
        self.norm = compute_pixmap(self.icon_path, theme)

        self.setPixmap(self.norm)


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, normal_icon_path: str, highlighted_icon_path: str, theme: Theme, parent=None):
        super().__init__(parent)
        self.norm = None
        self.high = None

        self.normal_icon_path = normal_icon_path
        self.highlighted_icon_path = highlighted_icon_path

        self.applyTheme(theme)

    def applyTheme(self, theme: Theme):
        self.norm = compute_pixmap(self.normal_icon_path, theme)
        self.high = compute_pixmap(self.highlighted_icon_path, theme)

        self.setPixmap(self.norm)

    def enterEvent(self, event):
        self.setPixmap(self.high)

    def leaveEvent(self, event):
        self.setPixmap(self.norm)

    def mousePressEvent(self, event):
        self.clicked.emit()

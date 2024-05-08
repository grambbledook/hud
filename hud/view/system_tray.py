from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QApplication

from hud.configuration.config import Config, BRIGHT, DARK
from hud.view.metrics_window import MetricsWindow
from hud.view.trainer_window import TrainerWindow


class SystemTray(QSystemTrayIcon):

    def __init__(self, metrics_window: MetricsWindow, trainer_window: TrainerWindow, app_config: Config, parent=None):
        super().__init__(parent)

        self.app_config = app_config
        self.metrics_window = metrics_window
        self.trainer_window = trainer_window

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.app_config.asset("hrm.png")))

        self.switch_theme = QAction("Switch Theme", self)
        self.switch_theme.triggered.connect(self.switchTheme)

        self.hide_buttons = QAction("Hide Buttons", self)
        self.hide_buttons.triggered.connect(self.toggleHideButtons)

        self.quit_action = QAction("Quit", self)
        self.quit_action.triggered.connect(self.quitApp)

        self.tray_icon_menu = QMenu()
        self.tray_icon_menu.addAction(self.switch_theme)
        self.tray_icon_menu.addAction(self.hide_buttons)
        self.tray_icon_menu.addAction(self.quit_action)
        self.tray_icon.setContextMenu(self.tray_icon_menu)
        self.tray_icon.show()

    def switchTheme(self):
        if self.app_config.hud_layout.theme == BRIGHT:
            self.app_config.hud_layout.theme = DARK
        else:
            self.app_config.hud_layout.theme = BRIGHT

        self.metrics_window.switchTheme()
        self.trainer_window.switchTheme()

    def toggleHideButtons(self):
        self.app_config.hud_layout.show_buttons = not self.app_config.hud_layout.show_buttons

        if self.app_config.hud_layout.show_buttons:
            self.hide_buttons.setText("Hide Buttons")
        else:
            self.hide_buttons.setText("Show Buttons")

        self.metrics_window.toggleHideButtons()
        self.trainer_window.toggleHideButtons()

    def quitApp(self):
        self.tray_icon.hide()
        self.metrics_window.quitApp()
        self.trainer_window.quitApp()
        QApplication.quit()
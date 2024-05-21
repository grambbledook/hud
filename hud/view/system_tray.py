from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QApplication

from hud.configuration.config import Config
from hud.view.navigator import ViewNavigator


class SystemTray(QSystemTrayIcon):

    def __init__(self, app_config: Config, view_navigator: ViewNavigator, parent=None):
        super().__init__(parent)

        self.app_config = app_config
        self.view_navigator = view_navigator

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
        self.view_navigator.switch_schema()

    def toggleHideButtons(self):
        print("Oops, toggling buttons haven't been implemented yet")

    def quitApp(self):
        self.tray_icon.hide()
        self.view_navigator.progress_to_state(9)
        QApplication.quit()

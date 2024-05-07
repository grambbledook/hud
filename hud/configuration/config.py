from dataclasses import dataclass
from os import path
from typing import Optional, Tuple


@dataclass
class Theme:
    colour_scheme: str
    background_colour: Tuple[int, int, int]


@dataclass
class HudLayout:
    theme: Theme
    show_buttons: bool = True


DARK = Theme(
    colour_scheme="""
        QListWidget {
            background-color: transparent;
            color: white;
            font-weight: bold;
            font-size: 20px;
            text-align: center;
        }
        QListWidget::item {
            background-color: transparent;
        }
        QListWidget::item:selected {
            background-color: #808080;
        }
        QLabel {
            color: white;
            font-weight: bold;
            font-size: 32px;
            text-align: center;
        }
    """,
    background_colour=(0, 0, 0),
)

BRIGHT = Theme(
    colour_scheme="""
        QListWidget {
            background-color: transparent;
            color: black;
            font-weight: bold;
            font-size: 20px;
            text-align: center;
        }
        QListWidget::item {
            background-color: transparent;
        }
        QListWidget::item:selected {
            background-color: #808080;
        }
        QLabel {
            color: black;
            font-weight: bold;
            font-size: 32px;
            text-align: center;
        }
    """,
    background_colour=(255, 255, 255),
)


@dataclass
class Config:
    connect_on_start: bool = False
    hud_layout: HudLayout = HudLayout(theme=DARK, show_buttons=True)
    app_dir: str = ""
    config_file: str = "config.yaml"
    log_file: Optional[str] = None
    assets_directory: str = "assets"

    def asset(self, name: str) -> str:
        return path.join(self.assets_directory, name)

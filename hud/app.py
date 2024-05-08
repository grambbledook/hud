import asyncio
import sys
from os import path

from PySide6.QtCore import QThreadPool
from qasync import QApplication, QEventLoop

from hud.configuration.config import Config
from hud.controller.controller import DeviceController
from hud.model.model import Model
from hud.service.ble.cycling_speed_cadence_service import CyclingCadenceAndSpeedService
from hud.service.ble.fec_bike_trainer_service import FecBikeTrainerService
from hud.service.ble.heart_rate_service import HeartRateService
from hud.service.ble.power_meter_service import PowerService
from hud.service.ble.scanner import BleDiscoveryService
from hud.service.data_management_service import DataManagementService
from hud.service.device_registry import DeviceRegistry
from hud.view.metrics_window import MetricsWindow
from hud.view.system_tray import SystemTray
from hud.view.trainer_window import TrainerWindow


def arrange_and_show(metrics_widget: MetricsWindow, trainer_widget: TrainerWindow):
    x, y = 100, 100
    metrics_widget.move(x, y)
    trainer_widget.move(x, y + metrics_widget.height())

    metrics_widget.show()
    trainer_widget.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    QThreadPool.globalInstance().setMaxThreadCount(10)
    pool = QThreadPool.globalInstance()

    model = Model()
    registry = DeviceRegistry()

    discovery_service = BleDiscoveryService(pool, model)
    hr_service = HeartRateService(pool, model, registry)
    csc_service = CyclingCadenceAndSpeedService(pool, model, registry)
    power_service = PowerService(pool, model, registry)
    legacy_bike_trainer_service = FecBikeTrainerService(pool, model, registry)

    app_config = Config()
    app_config.assets_directory = path.join(path.dirname(path.abspath(__file__)), app_config.assets_directory)

    config_service = DataManagementService(
        model=model,
        hr_service=hr_service,
        csc_service=csc_service,
        power_service=power_service,
        legacy_bike_trainer_service=legacy_bike_trainer_service,
    )

    controller = DeviceController(
        scan_service=discovery_service,
        hr_service=hr_service,
        csc_service=csc_service,
        power_service=power_service,
        legacy_bike_trainer_service=legacy_bike_trainer_service,
        config_service=config_service
    )

    metrics_widget = MetricsWindow(app_config, controller, model)
    trainer_widget = TrainerWindow(app_config, controller, model)

    arrange_and_show(metrics_widget, trainer_widget)

    tray = SystemTray(app_config=app_config, metrics_window=metrics_widget, trainer_window=trainer_widget)
    tray.show()

    with loop:
        sys.exit(app.exec())

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
from hud.view.sensor.sensor_window import SensorsWindow
from hud.view.navigator import ViewNavigator
from hud.view.system_tray import SystemTray
from hud.view.trainer.trainer_window import TrainerWindow
from hud.view.workout.workout_window import WorkoutWindow
from hud.view.workout_statistics.workout_statistics_window import WorkoutStatisticsWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    QThreadPool.globalInstance().setMaxThreadCount(10)
    pool = QThreadPool.globalInstance()

    model = Model()
    registry = DeviceRegistry()

    mock_mode = True
    discovery_service = BleDiscoveryService(pool, model, mock_mode=mock_mode)
    hr_service = HeartRateService(pool, model, registry, mock_mode=mock_mode)
    csc_service = CyclingCadenceAndSpeedService(pool, model, registry, mock_mode=mock_mode)
    power_service = PowerService(pool, model, registry, mock_mode=mock_mode)
    legacy_bike_trainer_service = FecBikeTrainerService(pool, model, registry, mock_mode=mock_mode)

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

    sensors_widget = SensorsWindow(app_config, controller, model)
    trainer_widget = TrainerWindow(app_config, controller, model)
    workout_widget = WorkoutWindow(app_config, controller, model)
    workout_statistic_widget = WorkoutStatisticsWindow(app_config)
    view_navigator = ViewNavigator(
        app_config=app_config,
        trainer_choice_window=trainer_widget,
        additional_sensors_window=sensors_widget,
        workout_window=workout_widget,
        workout_statistics_window=workout_statistic_widget,

    )
    view_navigator.apply()

    tray = SystemTray(app_config=app_config, view_navigator=view_navigator)
    tray.show()

    with loop:
        sys.exit(app.exec())

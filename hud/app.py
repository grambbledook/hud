import asyncio
import sys
from os import path

from PySide6.QtCore import QThreadPool
from qasync import QApplication, QEventLoop

from hud.configuration.config import Config
from hud.controller.controller import DeviceController
from hud.model.model import Model
from hud.service.ble.cycling_speed_cadence_service import CyclingCadenceAndSpeedService
from hud.service.ble.heart_rate_service import HeartRateService
from hud.service.ble.power_meter_service import PowerService
from hud.service.ble.scanner import BleDiscoveryService
from hud.service.data_management_service import DataManagementService
from hud.service.device_registry import DeviceRegistry
from hud.view.hud_window import HUDView

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

    app_config = Config()
    app_config.assets_directory = path.join(path.dirname(path.abspath(__file__)), app_config.assets_directory)

    config_service = DataManagementService(
        model=model,
        hr_service=hr_service,
        csc_service=csc_service,
        power_service=power_service,
    )

    controller = DeviceController(
        scan_service=discovery_service,
        hr_service=hr_service,
        csc_service=csc_service,
        power_service=power_service,
        config_service=config_service
    )

    view = HUDView(app_config, controller, model)
    view.show()

    with loop:
        sys.exit(app.exec())

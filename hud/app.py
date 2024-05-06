import asyncio
import sys

from PySide6.QtCore import QThreadPool
from qasync import QApplication, QEventLoop

from hud.config import Config
from hud.controller import DeviceController
from hud.services import Model, BleDiscoveryService, CyclingCadenceAndSpeedService, HrmService, PowerService, \
    DeviceRegistry, DataManagementService
from hud.view import HUDView

if __name__ == "__main__":
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    QThreadPool.globalInstance().setMaxThreadCount(10)
    pool = QThreadPool.globalInstance()

    model = Model()
    registry = DeviceRegistry()

    discovery_service = BleDiscoveryService(pool, model)
    hr_service = HrmService(pool, model, registry)
    csc_service = CyclingCadenceAndSpeedService(pool, model, registry)
    power_service = PowerService(pool, model, registry)

    app_config = Config()

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

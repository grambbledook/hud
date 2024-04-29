import asyncio
import sys

from PyQt5.QtCore import QThreadPool
from qasync import QApplication, QEventLoop

from hud.controller import DeviceController
from hud.services import Model, BleDiscoveryService, CyclingCadenceAndSpeedService, HrmService, PowerService, \
    DeviceRegistry
from hud.view import HUDView, BRIGHT

if __name__ == "__main__":
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    QThreadPool.globalInstance().setMaxThreadCount(10)
    QThreadPool.globalInstance().setStackSize(2048)
    pool = QThreadPool.globalInstance()

    model = Model()

    registry = DeviceRegistry()

    controller = DeviceController(
        scan_service=BleDiscoveryService(pool, model),
        hrm_service=HrmService(pool, model, registry),
        csc_service=CyclingCadenceAndSpeedService(pool, model, registry),
        power_service=PowerService(pool, model, registry),
    )

    view = HUDView(controller, model, style=BRIGHT)
    view.show()

    with loop:
        sys.exit(app.exec_())

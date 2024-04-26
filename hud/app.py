import asyncio
import sys

from PyQt5.QtCore import QThreadPool
from qasync import QApplication, QEventLoop

from hud.controller import DeviceController
from hud.services import Model, BleDiscoveryService, CyclingCadenceAndSpeedService
from hud.view import HUDView

if __name__ == "__main__":
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    QThreadPool.globalInstance().setMaxThreadCount(10)
    QThreadPool.globalInstance().setStackSize(2048)
    pool = QThreadPool.globalInstance()

    model = Model()

    controller = DeviceController(
        scan_service=BleDiscoveryService(pool, model),
        hrm_service=CyclingCadenceAndSpeedService(pool, model),
        csc_service=CyclingCadenceAndSpeedService(pool, model),
    )

    view = HUDView(controller, model)
    view.show()

    with loop:
        sys.exit(app.exec_())

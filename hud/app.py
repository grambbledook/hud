import asyncio
import sys

from PyQt5.QtCore import QThreadPool
from qasync import QApplication, QEventLoop

from hud.controller import Controller, DeviceChannel
from hud.model import HUDModel
from hud.view import HUDView

if __name__ == "__main__":
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    hrm_channel = DeviceChannel()
    cad_channel = DeviceChannel()
    spd_channel = DeviceChannel()
    pwr_channel = DeviceChannel()

    view = HUDView(
        hrm_channel=hrm_channel,
        cad_channel=cad_channel,
        spd_channel=spd_channel,
        pwr_channel=pwr_channel,
    )

    QThreadPool.globalInstance().setMaxThreadCount(10)
    QThreadPool.globalInstance().setStackSize(2048)
    model = HUDModel(QThreadPool.globalInstance())

    controller = Controller(
        hrm_channel=hrm_channel,
        cad_channel=cad_channel,
        spd_channel=spd_channel,
        pwr_channel=pwr_channel,
        model=model,
    )

    view.show()

    with loop:
        sys.exit(app.exec_())

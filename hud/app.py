import asyncio
import sys

from PyQt5.QtCore import QThreadPool
from qasync import QApplication, QEventLoop

from hud.controller import Controller
from hud.model import HUDModel
from hud.view import HUDView

if __name__ == "__main__":
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    view = HUDView()
    model = HUDModel()

    controller = Controller(model, view)
    QThreadPool.globalInstance().setMaxThreadCount(10)
    QThreadPool.globalInstance().setStackSize(2048)  # Set the stack size to 2048 bytes# Set the maximum thread count to 10
    view.show()

    with loop:
        sys.exit(app.exec_())

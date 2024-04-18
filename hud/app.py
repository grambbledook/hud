import asyncio
import sys

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

    view.show()
    sys.exit(app.exec_())

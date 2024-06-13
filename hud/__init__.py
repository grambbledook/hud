from PySide6.QtAsyncio import QAsyncioTask

# Monkey patch QtAsyncio to allow Bleak connections to be established w/o 'QtTask.xxx is not implemented' error
QAsyncioTask.cancelling = lambda self: False
QAsyncioTask.uncancel = lambda self: 999
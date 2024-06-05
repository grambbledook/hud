from PySide6.QtAsyncio import QAsyncioTask

# Monkey patch QtAsyncio to allow Bleak connections to be established w/o 'QtTask.cancelling is not implemented' error
QAsyncioTask.cancelling = lambda self: False

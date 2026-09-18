from PySide6.QtCore import QObject, QRunnable, Signal, Slot

class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)

class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__(); self.fn=fn; self.args=args; self.kwargs=kwargs; self.signals=WorkerSignals()
    @Slot()
    def run(self):
        try:self.signals.finished.emit(self.fn(*self.args,**self.kwargs))
        except Exception as e:self.signals.error.emit(str(e))

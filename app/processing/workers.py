"""
ALAS — Processing Workers
Base classes to run heavy tasks in separate threads.
"""

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot


class ProcessingWorkerSignals(QObject):
    """Signals emitted by processing workers."""
    started = pyqtSignal()
    progress = pyqtSignal(int)          # 0-100
    status = pyqtSignal(str)            # status message
    result = pyqtSignal(object)         # processing result
    error = pyqtSignal(str)             # error message
    finished = pyqtSignal()


class ProcessingWorker(QRunnable):
    """Base worker for background processing tasks."""

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = ProcessingWorkerSignals()
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self):
        self.signals.started.emit()
        try:
            result = self.func(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class FileLoadWorker(ProcessingWorker):
    """Specific worker for file loading."""

    def __init__(self, file_path: str, loader_func, **kwargs):
        super().__init__(loader_func, file_path, **kwargs)
        self.file_path = file_path


class ProgressCallback:
    """Callback to report progress from processing functions."""

    def __init__(self, signals: ProcessingWorkerSignals = None):
        self.signals = signals

    def update(self, progress: int, message: str = ""):
        if self.signals:
            self.signals.progress.emit(progress)
            if message:
                self.signals.status.emit(message)

    def __call__(self, progress: int, message: str = ""):
        self.update(progress, message)

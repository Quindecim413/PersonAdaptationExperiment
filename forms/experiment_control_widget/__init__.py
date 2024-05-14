import typing
from PyQt6 import QtCore, QtGui
from experiments_common.experiment_progress_control import ExperimentProgressControl

from forms.configure_experiment_widget import CurrentConfig
from .ui_ExperimentControlWidget import Ui_ExperimentControlWidget
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QTimer

ExperimentProgressControl


# class ExperimentControlWidget(QWidget):
#     started = pyqtSignal(CurrentConfig)
#     finished = pyqtSignal(bool) #early-stopping
#     progressed = pyqtSignal(int, int)

#     def __init__(self, cached_config=None, parent=None) -> None:
#         super().__init__(parent)
#         self.setup_ui()

#         self._ui.configs._ui.num_commands.valueChanged.connect(self._ui.progressBar.setMaximum)

#         self.set_config(cached_config)
#         self._timer = QTimer()
#         self._timer.timeout.connect(self._update_progress)
#         self._command_ind = 0
        
#         self._ui.start_button.clicked.connect(self._start)
#         self._ui.stop_button.clicked.connect(self._interrupt)

#         self.set_running(False)
    
#     def set_config(self, config: CurrentConfig):
#         self._ui.configs.restore_experiment_config(config)
#         print(config)
#         if config is not None:
#             self._ui.progressBar.setMaximum(config.num_commands)
    
#     def setup_ui(self):
#         self._ui = Ui_ExperimentControlWidget()
#         self._ui.setupUi(self)

#     def set_running(self, is_running):
#         self._ui.configs.setEnabled(not is_running)
#         self._ui.start_button.setEnabled(not is_running)
#         self._ui.stop_button.setEnabled(is_running)
#         # self._ui.progressBar.reset()
    
#     def current_experiment_config(self):
#         return self._ui.configs.experiment_config()

#     @pyqtSlot()
#     def _start(self):
#         configs = self.current_experiment_config()
#         self._timer.setInterval(int(configs.command_time*1000))
#         self._command_ind = 0
#         self._ui.progressBar.setMaximum(configs.num_commands)
#         self._ui.progressBar.setValue(0)
        
#         self.set_running(True)
#         self._timer.start()
#         self.started.emit(self.current_experiment_config())
    
#     def _finish(self):
#         self._timer.stop()
#         self.finished.emit(False)
#         self.set_running(False)

#     @pyqtSlot()
#     def _interrupt(self):
#         self._timer.stop()
#         self.finished.emit(True)
#         self.set_running(False)

#     def _update_progress(self):
#         self._ui.progressBar.setValue(self._command_ind+1)

#         self._command_ind += 1
#         configs = self.current_experiment_config()
#         if self._command_ind >= configs.num_commands:
#             self._finish()
#         else:
#             self.progressed.emit(self._command_ind, configs.num_commands)
    

class ExperimentControlWidget(QWidget):
    started = pyqtSignal(CurrentConfig)
    finished = pyqtSignal(bool) #early-stopping
    progressed = pyqtSignal(int, int)

    def __init__(self, cached_config=None, parent=None) -> None:
        super().__init__(parent)
        self.setup_ui()
        self._experiment_control = ExperimentProgressControl(self)
        self._experiment_control.experiment_started.connect(self._experiment_started)
        self._experiment_control.experiment_progressed.connect(self._experiment_progressed)
        self._experiment_control.experiment_interrupted.connect(self._experiment_interrupted)
        self._experiment_control.experiment_finished.connect(self._experiment_finished)

        self._ui.configs._ui.num_commands.valueChanged.connect(self._ui.progressBar.setMaximum)
        self.set_config(cached_config)
        
        self._ui.start_button.clicked.connect(self._start_clicked)
        self._ui.stop_button.clicked.connect(self._stop_clicked)

        self.set_running(False)
    
    def set_config(self, config: CurrentConfig):
        self._ui.configs.restore_experiment_config(config)
        print(config)
        if config is not None:
            self._ui.progressBar.setMaximum(config.num_commands)
    
    def setup_ui(self):
        self._ui = Ui_ExperimentControlWidget()
        self._ui.setupUi(self)

    def set_running(self, is_running):
        self._ui.configs.setEnabled(not is_running)
        self._ui.start_button.setEnabled(not is_running)
        self._ui.stop_button.setEnabled(is_running)
        self._ui.progressBar.setValue(0)
    
    def current_experiment_config(self):
        return self._ui.configs.experiment_config()

    @pyqtSlot(CurrentConfig)
    def _experiment_started(self, configs: CurrentConfig):
        self._ui.progressBar.setMaximum(configs.num_commands)
        self._ui.progressBar.setValue(0)
        self.set_running(True)
        self.started.emit(self.current_experiment_config())

    @pyqtSlot(int, int)
    def _experiment_progressed(self, command_ind:int, max_commands:int):
        self._ui.progressBar.setValue(command_ind+1)
        self._ui.progressBar.setMaximum(max_commands)
        self.progressed.emit(command_ind, max_commands)

    @pyqtSlot()
    def _experiment_interrupted(self):
        self.set_running(False)
        self.finished.emit(True)

    @pyqtSlot()
    def _experiment_finished(self):
        self.set_running(False)
        self.finished.emit(False)        

    @pyqtSlot()
    def _start_clicked(self):
        configs = self.current_experiment_config()
        self._experiment_control.start(configs)
    
    @pyqtSlot()
    def _stop_clicked(self):
        self._experiment_control.interrupt()

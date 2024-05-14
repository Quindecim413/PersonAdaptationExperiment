import typing
from PyQt6.QtCore import QObject, QTimer, pyqtSlot, pyqtSignal
from dataclasses import dataclass
from utils.experiment_configs_model import CurrentConfig
from time import time

@dataclass(frozen=True)
class CommandRecord:
    time_recorder: float
    code: int


class ExperimentProgressControl(QObject):
    experiment_started = pyqtSignal(CurrentConfig)
    experiment_progressed = pyqtSignal(int, int)
    experiment_finished = pyqtSignal()
    experiment_interrupted = pyqtSignal()

    def __init__(self, parent: QObject | None =None) -> None:
        super().__init__(parent)
        self._timer = QTimer()
        self._timer.timeout.connect(self._progress)
        self._command_ind = 0
        self._last_running_experiment_config:CurrentConfig = None
        self._recorded_commands: typing.List[CommandRecord] = []
        self._recording_command_code = None
        self._num_commands_forced = 0
    
    def start(self, experiment_config: CurrentConfig):
        self._command_ind = -1
        self._num_commands_forced = 0
        self._last_running_experiment_config = experiment_config
        self._timer.setSingleShot(True)
        self._timer.setInterval(int(experiment_config.command_time*1000))
        self._timer.start()
        self.experiment_started.emit(experiment_config)

    def interrupt(self):
        self._stop(True)

    def is_running(self):
        return self._timer.isActive()
    
    def _progress(self):
        configs = self._last_running_experiment_config
        self._command_ind += 1
        if self._command_ind >= configs.num_commands:
            print('self._command_ind >= configs.num_commands', self._command_ind >= configs.num_commands, self._command_ind, configs.num_commands)
            self._stop(False)
        else:
            print(self._command_ind, configs.num_commands)
            self.experiment_progressed.emit(self._command_ind, configs.num_commands)
            self._timer.start()
    
    def _force_next_command(self):
        self._num_commands_forced += 1
        self._timer.stop()
        self._progress()

    def num_commands_timeouted(self):
        if self._last_running_experiment_config is None and self._command_ind >= 0:
            return 0
        return self._command_ind - self._num_commands_forced

    def num_commands_executed_successfully(self):
        if self._last_running_experiment_config is None and self._command_ind >= 0:
            return 0
        return self._num_commands_forced

    def update_recording_command(self, command_code: int|None):
        self._recorded_commands = []
        self._recording_command_code = command_code
    
    def add_best_match_command(self, command_code: int):
        if not self.is_running():
            return
        if command_code is None:
            return
        
        now = time()
        timeout = self._last_running_experiment_config.command_capture_time
        recording_command_code = self._recording_command_code
        
        if recording_command_code is None:
            return
        if timeout == 0:
            # При выставлении значения удержания == 0, не проводим анализ плотности удержания команды
            return
        
        recorded_commands = list(filter(lambda com: now - com.time_recorder < timeout, self._recorded_commands))
        recorded_commands.append(CommandRecord(now, command_code))
        density = sum(map(lambda com: com.code == recording_command_code, recorded_commands))
        if len(recorded_commands) == 0:
            density = 0
        else:
            density /= len(recorded_commands)
        
        timeperiod = now - min(map(lambda com: com.time_recorder, recorded_commands))
        self._recorded_commands = recorded_commands

        # print('timeperiod =', timeperiod, 'density =', density, end='')

        if timeperiod < timeout * 0.95:
            # print(f'bad time period, {timeperiod} < {timeout * 0.95}')
            return

        if density < 0.9:
            # print(f'bad density {density}')
            return
        
        self._force_next_command()    
        
    def _stop(self, early_stopping:bool):
        if self._timer.remainingTime() > 0:
            self._timer.stop()
        self._recorded_commands = []
        self._recording_command_code = None
        
        if early_stopping:
            self.experiment_interrupted.emit()
        else:
            self.experiment_finished.emit()
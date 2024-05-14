import typing
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt6.QtMultimedia import QCamera

from utils.experiment_configs_model import ExperimentConfigsModel


# class Model(QObject):
#     camera_device_changed = pyqtSlot()

#     def __init__(self, parent) -> None:
#         super().__init__(parent)
#         self.experiment_config_model = ExperimentConfigsModel()
#         self._camera_device = None
#         self._running_hand_experiment = False
#         self._running_head_experiment = False
#         self._running_eyes_experiment = False

#     def is_running_experiment(self):
        
    
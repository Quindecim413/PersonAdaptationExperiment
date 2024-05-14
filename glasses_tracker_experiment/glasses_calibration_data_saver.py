from typing import List
import h5py
from experiments_common.data_saver import DataSaver, Field
from h5py import Group
import time
from pickle import dumps
from glasses_tracker_experiment.glasses_callibrator import ModelCalibrationResult
import numpy as np

NUM_SENSORS = 3

class GlassesCallibrationDataSaver(DataSaver):
    def __init__(self, save_file) -> None:
        super().__init__(save_file, 'glasses_callibration')

    def _save_fields(self) -> List[Field]:
        fields = [
            Field('command_ind', (1,), 'i8', -1),
            Field('command_code', (1,), 'i8', -1),
            Field('target_rel', (2,), np.float32),
            Field('target_pix', (2,), np.float32),
            Field('sensors_data', (NUM_SENSORS,), np.float32)
        ]
        return fields

    def add_callibration_result(self, results: ModelCalibrationResult):
        self.save_dataset('callibration_results', np.void(dumps(results)))
        self.append_attrs(**{'mae': results.mae})

    def append_data(self, command_ind, command_code, target_rel, target_pix, sensors_data):
        self._append_data(command_ind, command_code, target_rel, target_pix, sensors_data)
    

        
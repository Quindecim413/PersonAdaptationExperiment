from typing import List
import h5py
from experiments_common.data_saver import DataSaver, Field
from h5py import Group
import time


NUM_SENSORS = 3


class GlassesDataSaver(DataSaver):
    def __init__(self, save_file) -> None:
        super().__init__(save_file, 'glasses')

    def create_person_dataset(self, person_name: str, person_test_id: str, show_cursor: bool, num_commands: int, sec_per_command: float, 
                              target_form_width: int, target_form_height: int,
                              view_width: int, view_height: int,
                              calibration_dataset_id: str):
         return super().create_person_dataset(person_name, person_test_id, show_cursor, num_commands, sec_per_command, 
                                              target_form_width, target_form_height, 
                                              view_width, view_height,
                                              **{'calibration_dataset_id': calibration_dataset_id})

    def _save_fields(self) -> List[Field]:
        fields = [
            Field('command_ind', (1,), 'i8', -1),
            Field('command_code', (1,), 'i8', -1),
            Field('target_rel', (2,), float),
            Field('target_pix', (2,), float),
            Field('sensors_data', (NUM_SENSORS,), float),
            Field('best_match_command_code', (1,), 'i8', -1),
            Field('best_match_command_pix', (2,), float),
            Field('predicted_intersection_pix', (2,), float)
        ]
        return fields
    
    def append_data(self, command_ind, command_code, target_rel, target_pix, sensors_data,
                    best_match_command_code, best_match_command_pos, predicted_intersection_pix):
        self._append_data(command_ind, command_code, target_rel, target_pix, sensors_data,
                          best_match_command_code, best_match_command_pos, predicted_intersection_pix)
    

        
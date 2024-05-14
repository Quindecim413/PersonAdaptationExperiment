from typing import List
from experiments_common.data_saver import DataSaver, Field
import numpy as np
import h5py

from hand_tracker_experiment.aruco_markers_detector import ArucoMarker


class HandDataSaver(DataSaver):
    def __init__(self, save_file) -> None:
        super().__init__(save_file, 'hand')

    def create_person_dataset(self, camera_name, person_name: str, person_test_id: str, show_cursor: bool, num_commands: int, sec_per_command: float, 
                              target_form_width: int, target_form_height: int,
                              view_width: int, view_height: int,
                              preview_image: np.ndarray, markers: List[ArucoMarker]):
        super().create_person_dataset(
                                      person_name,
                                      person_test_id, 
                                      show_cursor, 
                                      num_commands, 
                                      sec_per_command, 
                                      target_form_width, 
                                      target_form_height,
                                      view_width, view_height
                                      )
        markers_descriptions = [marker.to_json() for marker in markers]
        self.append_attrs(camera_name=camera_name, markers=markers_descriptions)
        self.save_dataset('preview_image', preview_image, np.uint8)
                                
    
    def _save_fields(self) -> List[Field]:
        fields = [
            Field('command_ind', (1,), 'i8', -1),
            Field('command_code', (1,), 'i8', -1),
            Field('target_rel', (2,), float),
            Field('target_pix', (2,), float),
            Field('best_match_command_code', (1,), 'i8', -1),
            Field('best_match_command_pix', (2,), float),
            Field('finger_tip_pix', (2,), float),
            Field('hand_landmarks', (21, 3), float),
            Field('hand_world_landmarks', (21, 3), float),
            Field('hand_visible', (1,), 'i8')
        ]
        return fields

    def append_data(self, command_ind, command_code, target_rel, target_pix, 
                    best_match_command_code, best_match_command_pix,
                    finger_tip_pos,
                    hand_lanmarks, hand_world_landmarks,
                    hand_visible):
        self._append_data(command_ind, command_code, target_rel, target_pix,
                          best_match_command_code, best_match_command_pix,
                          finger_tip_pos,
                          hand_lanmarks, hand_world_landmarks,
                          1 if hand_visible else 0)
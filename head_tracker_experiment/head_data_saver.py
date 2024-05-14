from typing import List
from experiments_common.data_saver import DataSaver, Field


class HeadDataSaver(DataSaver):
    def __init__(self, save_file) -> None:
        super().__init__(save_file, 'head')

    def create_person_dataset(self, camera_name, person_name: str, person_test_id: str, show_cursor: bool, num_commands: int, sec_per_command: float, 
                              target_form_width: int, target_form_height: int,
                              view_width: int, view_height: int,
                                **meta_args):
        super().create_person_dataset(person_name, person_test_id, show_cursor, num_commands, sec_per_command, 
                                      target_form_width, target_form_height,
                                      view_width, view_height, 
                                      **meta_args)
        self.append_attrs(camera_name=camera_name)
    def _save_fields(self) -> List[Field]:
        fields = [
            Field('command_ind', (1,), 'i8', -1),
            Field('command_code', (1,), 'i8', -1),
            Field('target_rel', (2,), float),
            Field('target_pix', (2,), float),
            Field('target_3d', (3,), float),
            Field('best_match_command_code', (1,), 'i8', -1),
            Field('best_match_command_pix', (2,), float),
            Field('intersection_pix', (2,), float),
            Field('intersection_3d', (3,), float),
            Field('head_transform', (4, 4), float),
            Field('head_visible', (1,), 'i8')
        ]
        return fields

    def append_data(self, command_ind, command_code, target_rel, target_pix, target_3d, 
                    best_match_command_code, best_match_command_pix,
                    intersetion_pix, intersection_3d, head_transform,
                    head_visible):
        self._append_data(command_ind, command_code, target_rel, target_pix, target_3d, 
                          best_match_command_code, best_match_command_pix,
                          intersetion_pix, intersection_3d, head_transform,
                          1 if head_visible else 0)
    

        
from typing import Any, Callable, List
import h5py
from datetime import datetime
import numpy as np
from PyQt6.QtCore import QObject, QThreadPool, QMutexLocker, QMutex
from dataclasses import dataclass, replace 
from utils.threading import Worker
import time
from datetime import datetime


@dataclass(frozen=True)
class Field:
    name: str # name for data array in h5py dataset
    data_shape: np.ndarray|tuple # data shape in one line record
    dtype: str|np.dtype|None
    default_value: Any|Callable = np.nan

@dataclass(frozen=True)
class FieldWithArrays:
    field: Field
    tmp_array: list


class DataSaver:
    def __init__(self, save_file, experiment_tag) -> None:
        print('saving', save_file)
        self._save_file = save_file
        
        self._current_person = None
        self._current_person_id = None
        self._fields_with_array: List[FieldWithArrays] = []
        self._experiment_tag = experiment_tag

        self._mutex_lock = QMutexLocker(QMutex())
    
    def _get_person_experiment_group(self, _file: h5py.File, experiment_tag, person_name):
        if _file.get(experiment_tag) is None:
            group = _file.create_group(experiment_tag)
        else:
            group = _file[self._experiment_tag]
        
        if group.get(person_name) is None:
            group = group.create_group(f'{person_name}')
        else:
            group = group[person_name]
        
        return group
    
    def _get_person_group_last_experiment_key(self, person_group: h5py.Group) -> int:
        return max([int(key) for key in [-1, *person_group.keys()]])
    
    def _get_person_group_last_experiment_group(self, person_group: h5py.Group) -> h5py.Group:
        key = self._get_person_group_last_experiment_key(person_group)
        group = person_group[str(key)]
        return group

    def _get_person_group_new_experiment_group(self, person_group: h5py.Group) -> h5py.Group:
        new_key = self._get_person_group_last_experiment_key(person_group) + 1
        group = person_group.create_group(str(new_key))
        return group


    def create_person_dataset(self, person_name:str, person_test_id:str, show_cursor:bool, num_commands:int, sec_per_command:float,
                              scene_width:int, scene_height:int, view_width:int, view_height:int, **meta_args):
        with self._mutex_lock:
            with h5py.File(str(self._save_file), 'a') as _file:
                self._current_person = person_name
                self._current_person_id = person_test_id
                person_group = self._get_person_experiment_group(_file, self._experiment_tag, self._current_person)
                experiment_group = self._get_person_group_new_experiment_group(person_group)


                experiment_group.attrs['test_timestamp'] = datetime.now().isoformat()
                experiment_group.attrs['test_id'] = person_test_id
                experiment_group.attrs['show_cursor'] = 1 if show_cursor else 0
                experiment_group.attrs['start_time'] = datetime.now().timestamp()
                experiment_group.attrs['num_commands'] = num_commands
                experiment_group.attrs['sec_per_command'] = sec_per_command
                experiment_group.attrs['scene_width'] = int(scene_width)
                experiment_group.attrs['scene_height'] = int(scene_height)
                experiment_group.attrs['view_width'] = int(view_width)
                experiment_group.attrs['view_height'] = int(view_height)
                
                
                for key, arg in meta_args.items():
                    experiment_group.attrs[key] = arg
                # self._flush_data()

                fields = self._save_fields()
                fields.insert(0, Field('timestamp_sec', (1,), float, time.time))
                self._fields_with_array = []

                print('creating datasets at', experiment_group)
                for field in fields:
                    experiment_group.create_dataset(str(field.name), 
                                                (0, *field.data_shape), 
                                                maxshape=(None, *field.data_shape), 
                                                dtype=field.dtype, 
                                                chunks=(10000, *field.data_shape))
                    
                    self._fields_with_array.append(FieldWithArrays(field, []))

    def save_dataset(self, name, data, dtype=None):
        with self._mutex_lock:
            with h5py.File(str(self._save_file), 'a') as _file:
                person_group = self._get_person_experiment_group(_file, self._experiment_tag, self._current_person)
                experiment_group = self._get_person_group_last_experiment_group(person_group)
                experiment_group.create_dataset(name, data=data, dtype=dtype)


    def _save_fields(self) -> List[Field]:
        raise NotImplementedError()

    def __write_to_file_in_thread(self, current_person:str, datasets_names:List[str], tmp_arrays_copy: List[np.ndarray]):
        if len(tmp_arrays_copy) == 0 or len(datasets_names) == 0:
            return
        if len(tmp_arrays_copy[0]) == 0:
            return
        
        with h5py.File(str(self._save_file), 'a') as _file:
            person_group = self._get_person_experiment_group(_file, self._experiment_tag, current_person)
            experiment_group = self._get_person_group_last_experiment_group(person_group)
            print(experiment_group)
            datasets = []

            print(experiment_group.keys())

            for name in datasets_names:
                datasets.append(experiment_group[name])

            current_size = datasets[0].len()
            desired_size = current_size + len(tmp_arrays_copy[0])

            for dataset in datasets:
                dataset.resize(desired_size, axis=0)

            for dataset, tmp_array, name in zip(datasets, tmp_arrays_copy, datasets_names):
                # print(dataset, name, tmp_array, tmp_array.dtype)
                dataset[current_size:] = tmp_array

    def _flush_data(self):
        with self._mutex_lock:
            datasets_names = list(map(lambda f_a: str(f_a.field.name), self._fields_with_array))
            # do reshape on data to make ndims>=2 on final array, because h5py.Dataset can't resize arrays with ndims=1
            tmp_arrays = []
            for f_a in self._fields_with_array:
                try:
                    tmp_arrays.append(np.array(f_a.tmp_array, dtype=f_a.field.dtype).reshape(-1, *f_a.field.data_shape))
                except Exception as e:
                    print(f_a)
                    raise e
            
            if self._current_person is not None:
                w = Worker(self.__write_to_file_in_thread, self._current_person, datasets_names, tmp_arrays)
                QThreadPool.globalInstance().start(w)
            for f_a in self._fields_with_array:
                f_a.tmp_array.clear()

    def _append_data(self, *args):
        if self._current_person is None:
            return
        args = [None, *args]
        with self._mutex_lock:
            if len(args) != len(self._fields_with_array):
                raise ValueError(f'number of arguments mismatch, expected {len(self._fields_with_array)}, got {len(args)}.\n args={args}\nfield={self._fields_with_array}')
            for arg, f_a in zip(args, self._fields_with_array):
                if arg is None:
                    if f_a.field.data_shape == (1,):
                        if callable(f_a.field.default_value):
                            arg = f_a.field.default_value()
                        else:
                            arg = f_a.field.default_value
                    else:
                        arg = np.full(f_a.field.data_shape, 
                                      f_a.field.default_value() if callable(f_a.field.default_value) else f_a.field.default_value,
                                      dtype=f_a.field.dtype)
                f_a.tmp_array.append(arg)
        
    def append_attrs(self, **kw_args):
        with self._mutex_lock:
            with h5py.File(str(self._save_file), 'a') as _file:
                person_group = self._get_person_experiment_group(_file, self._experiment_tag, self._current_person)
                experiment_group = self._get_person_group_last_experiment_group(person_group)
                for key, val in kw_args.items():
                    experiment_group.attrs[key] = val


        if len(self._fields_with_array) > 0:
            if len(self._fields_with_array[0].tmp_array) > 10000:
                self._flush_data()

    def stop_save(self, early_stop):
        self._flush_data()
        with self._mutex_lock:
            with h5py.File(str(self._save_file), 'a') as _file:
                person_group = self._get_person_experiment_group(_file, self._experiment_tag, self._current_person)
                experiment_group = self._get_person_group_last_experiment_group(person_group)

                if self._current_person is not None:
                    experiment_group.attrs['early_stop'] = 1 if early_stop else 0
            
            self._current_person = None
            self._person_gr = None

    def is_writing_person_data(self):
        return self._current_person is not None
    
    def delete_current_record(self):
        with self._mutex_lock:
            if self._current_person is not None:
                with h5py.File(str(self._save_file), 'a') as _file:
                    person_group = self._get_person_experiment_group(_file, self._experiment_tag, self._current_person)
                    experiment_group = self._get_person_group_last_experiment_group(person_group)
                    del _file[experiment_group.name]

            self._current_person = None
            self._current_person_id = None

            for f_a in self._fields_with_array:
                f_a.tmp_array.clear()

    # def close(self):
    #     with self._mutex_lock:
    #         if self._file is not None:
    #             self._file.close()
    #             self._file = None

        
import typing
from PyQt6.QtCore import QObject, pyqtSignal
from dataclasses import dataclass, replace
from pathlib import Path
import sys, os
from dataclasses_json import dataclass_json
import json

import dataclasses_json.cfg

dataclasses_json.global_config.encoders[Path] = str
dataclasses_json.global_config.decoders[Path] = Path

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Path):
            return str(o)
        return super().default(o)


@dataclass_json
@dataclass(frozen=True)
class CurrentConfig:
    save_path: Path
    person_name: str
    test_id: str
    num_commands: int
    command_time: float
    command_capture_time: float
    show_cursor: bool


class ExperimentConfigsModel(QObject):
    config_changed = pyqtSignal(CurrentConfig)
    num_commands_changed = pyqtSignal(int)
    show_cursor_changed = pyqtSignal(bool)

    def __init__(self, parent: QObject | None = ...) -> None:
        super().__init__(parent)
        path = Path(__file__).parent.parent / 'experiment_results.hdf5'
        self.save_config_path = Path(__file__).parent.parent / 'configs.json'
        self.__experiment_config = CurrentConfig(path, 'Некто', '', 30, 2, 0.5, True)

    def config(self):
        return self.__experiment_config
    
    def save_to_file(self):
        d = self.__experiment_config.to_dict()
        with open(self.save_config_path, 'w', encoding='utf-8') as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
    def restore_from_file(self):
        if self.save_config_path.exists():
            with open(self.save_config_path, 'r', encoding='utf-8') as f:
                d = json.load(f)
            self.set_config(CurrentConfig.from_dict(d))

    def set_config(self, experiment_config: CurrentConfig):
        assert isinstance(experiment_config, CurrentConfig)
        self.__experiment_config = experiment_config
        self.config_changed.emit(self.__experiment_config)

    def set_show_cursor(self, value: bool):
        value = bool(value)
        if value != self.__experiment_config.show_cursor:
            self.__experiment_config = replace(self.__experiment_config, show_cursor=value)
            self.show_cursor_changed.emit(value)
    
    def show_cursor(self):
        return self.__experiment_config.show_cursor

    def set_num_commands(self, value: int):
        value = int(value)
        if value != self.__experiment_config.num_commands:
            self.__experiment_config = replace(self.__experiment_config, num_commands=value)
            self.num_commands_changed.emit(value)
    
    def num_commands(self):
        return self.__experiment_config.num_commands
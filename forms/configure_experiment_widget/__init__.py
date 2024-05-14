from pathlib import Path
from utils.experiment_configs_model import CurrentConfig, ExperimentConfigsModel
from .ui_ConfigureExperimentWidget import Ui_ConfigureExperimentWidget
from PyQt6.QtWidgets import QWidget, QFileDialog
from PyQt6.QtCore import pyqtSlot
from pathlib import Path


class ConfigureExperimentWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setup_ui()

        self._ui.select_save_path_btn.clicked.connect(self._show_select_path_dialog)
        self._ui.create_save_file_btn.clicked.connect(self._show_create_save_file_dialog)

    def setup_ui(self):
        self._ui = Ui_ConfigureExperimentWidget()
        self._ui.setupUi(self)
    
    @pyqtSlot()
    def _show_select_path_dialog(self):
        fname = QFileDialog.getOpenFileName(
            self,
            "Выберите файл сохранения",
            str(Path.cwd()),
            "Hdf55 Files (*.hdf5)",
        )
        if fname[0]:
            self._ui.save_path.setText(fname[0])
    
    @pyqtSlot()
    def _show_create_save_file_dialog(self):
        fname = QFileDialog.getSaveFileName(self,\
                                    'Укажите файл сохрания',
                                    str(Path.cwd()/'experiment_results.hdf5'),
                                    "Hdf55 Files (*.hdf5)")
        self._ui.save_path.setText(fname[0])
    
    def restore_experiment_config(self, cached_config: CurrentConfig):
        if cached_config is None:
            return
        self._ui.save_path.setText(str(cached_config.save_path.absolute()))
        self._ui.person_name.setText(cached_config.person_name)
        self._ui.test_id.setText(cached_config.test_id)
        self._ui.num_commands.setValue(cached_config.num_commands)
        self._ui.command_time.setValue(cached_config.command_time)
        self._ui.command_capture_time.setValue(cached_config.command_capture_time)
        self._ui.show_cursor.setChecked(cached_config.show_cursor)
    
    def experiment_config(self):
        save_path = Path(self._ui.save_path.text())
        person_name = self._ui.person_name.text()
        test_id = self._ui.test_id.text()
        num_commands = self._ui.num_commands.value()
        command_time = self._ui.command_time.value()
        command_capture_time = self._ui.command_capture_time.value()
        show_cursor = self._ui.show_cursor.isChecked()
        return CurrentConfig(save_path, person_name, test_id, num_commands, command_time, command_capture_time, show_cursor)
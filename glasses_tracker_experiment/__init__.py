from enum import Enum
import typing
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QPointF, QSize 
from PyQt6.QtWidgets import QWidget, QMainWindow, QMessageBox, QApplication
from PyQt6.QtGui import QAction, QActionGroup
from experiments_common.experiment_progress_control import ExperimentProgressControl
from experiments_common.grid_commands_generator import GridCommandsGenerator
from glasses_tracker_experiment.glasses_reader import GlassesReader
from glasses_tracker_experiment.ui_GlassesTrackerExperiment import Ui_GlassesTrackerExperiment

from utils.experiment_configs_model import CurrentConfig

from experiments_common.grid_commands_controller import GridCommandsController
from experiments_common.grid_experiment_drawer import GridExperimentDrawer
from glasses_tracker_experiment.glasses_calibration_data_saver import GlassesCallibrationDataSaver
from glasses_tracker_experiment.glasses_callibrator import GlassesCallibrator, ModelCalibrationResult
from glasses_tracker_experiment.glasses_data_saver import GlassesDataSaver
from utils.experiment_configs_model import CurrentConfig
from uuid import uuid4
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QTimer
import numpy as np
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo
from dataclasses import replace


NUM_SENSORS = 3

class CallibrationGridGenerator(GridCommandsGenerator):
    def generate_commands_sequence(self, n_commands):
        """
        5 3 7      0 1 2
        1 0 2  ->  3 4 5
        6 4 8      6 7 8
        """
        return np.arange(self.max_commands())
    
    def centers(self):
        v_span = self._vertical_span()
        h_span = self._horizontal_span()
        start_x = self._left_line()
        start_y = self._up_line()
        centers = []
        for j in range(3):
            for i in range(3):
                centers.append((start_x + h_span * (1/6 + i/3), start_y + v_span * (1/6 + j / 3)))
        centers = np.array(centers, float)
        if self.max_commands() == 5:
            inds = [4, 3, 5, 1, 7]
        elif self.max_commands() == 7:
            inds = [4, 3, 5, 0, 6, 2, 8]
        elif self.max_commands() == 9:
            inds = [4, 3, 5, 1, 7, 0, 6, 2, 8]
        else:
            raise ValueError('max_commands should be in [5, 7, 9]')
        return centers[inds]
    
    def codes(self):
        return np.arange(self.max_commands())

class ControllerState(Enum):
    FREE_RUN            = 0
    RUNNING_CALLIBRATION = 1
    RUNNING_EXPERIMENT  = 2

class GlassesTrackerExperiment:
    pass

class GlassesController(QObject):
    def __init__(self, drawer: GridExperimentDrawer,
                 commands_controller: GridCommandsController,
                 view_form: GlassesTrackerExperiment) -> None:
        super().__init__()
        self._drawer = drawer
        self._commands_controller = commands_controller
        self._last_calibration_id = None
        self._glasses_calib_result:ModelCalibrationResult = None
        self._view_form: GlassesTrackerExperiment = view_form
        self._reader: GlassesReader = None
        self._state = ControllerState.FREE_RUN
        self._process_data = True
        self._recieve_data_ind = 0
        self._making_command = False

        self._last_available_usb_ports: typing.List[QSerialPortInfo] = []
        self._check_connected_ports_timer = QTimer(self)
        self._check_connected_ports_timer.setInterval(300)
        self._check_connected_ports_timer.timeout.connect(self._check_usb_ports_availability)
        self._check_connected_ports_timer.start()

        self._experiment_control = ExperimentProgressControl(self)
        self._experiment_control.experiment_started.connect(self._experiment_started)
        self._experiment_control.experiment_progressed.connect(self._experiment_progressed)
        self._experiment_control.experiment_interrupted.connect(self._experiment_interrupted)
        self._experiment_control.experiment_finished.connect(self._experiment_finished)

        self._view_form.set_experiment_running(False)
        self._view_form.set_experiment_runnable(True)
        self._current_running_config: CurrentConfig = None


    def glasses_reader(self):
        return self._reader

    @pyqtSlot(CurrentConfig)
    def _experiment_started(self, experiment_config: CurrentConfig):
        self._making_command = False
        self._current_running_config = experiment_config

        self._view_form.set_num_commands(experiment_config.num_commands)
        self._view_form.set_experiment_running(True)
        self._view_form.set_experiment_runnable(False)
        if self._state == ControllerState.RUNNING_CALLIBRATION:
            self._view_form.set_show_cursor(False)
        else:
            print('experiment_config', experiment_config)
            self._view_form.set_show_cursor(experiment_config.show_cursor)
        
    def _progress_experiment(self, command_ind, max_commands):
        self._commands_controller.update_target_command_ind(command_ind)

    def _progress_callibration(self, command_ind, max_commands):
        self._commands_controller.update_target_command_ind(command_ind)
        
        com_ind, com = self._commands_controller.grid_commands_generator().current_target()
        
        if com is not None:
            self._experiment_control.update_recording_command(com.code)

    @pyqtSlot(int, int)
    def _experiment_progressed(self, command_ind: int, max_commands: int):
        self._making_command = True 

        if self._state == ControllerState.RUNNING_CALLIBRATION:
            self._progress_callibration(command_ind, max_commands)
        elif self._state == ControllerState.RUNNING_EXPERIMENT:
            self._progress_experiment(command_ind, max_commands)
        self._view_form.set_num_executed_commands(command_ind)
        ind, com = self._commands_controller.grid_commands_generator().current_target()
        if com is None:
            com_code = None
        else:
            com_code = com.code
        self._experiment_control.update_recording_command(com_code)

    @pyqtSlot()
    def _experiment_interrupted(self):
        self._commands_controller.update_target_command_ind(None)
        self._view_form.set_experiment_running(False)
        self._view_form.set_experiment_runnable(True)

        self._view_form.set_show_cursor(self._view_form.experiment_config().show_cursor)

        if self._state == ControllerState.FREE_RUN:
            return
        elif self._state == ControllerState.RUNNING_CALLIBRATION:
            self.stop_callibrate(True)
            self.set_processing_any_data(False)
            self._view_form.show_finish_experiment_msg_and_data_is_not_saved()
            self.set_processing_any_data(True)
        elif self._state == ControllerState.RUNNING_EXPERIMENT:
            self.set_processing_any_data(False)
            do_save = self._view_form.show_finish_experiment_msg_and_ask_if_to_save_data()
            self.stop_experiment(True, do_save)
            self.set_processing_any_data(True)

    @pyqtSlot()
    def _experiment_finished(self):
        self._commands_controller.update_target_command_ind(None)
        self._view_form.set_experiment_running(False)
        self._view_form.set_experiment_runnable(True)

        if self._state == ControllerState.RUNNING_CALLIBRATION:
            self.stop_callibrate()
        elif self._state == ControllerState.RUNNING_EXPERIMENT:
            self.stop_experiment()
        
        self._view_form.set_show_cursor(self._view_form.experiment_config().show_cursor)
        self._commands_controller.set_grid_commands_generator(GridCommandsGenerator(0))
        
        self._view_form.show_finish_experiment_msg(self._experiment_control.num_commands_executed_successfully(),
                                                   self._view_form.experiment_config().num_commands)

    def set_processing_any_data(self, value: bool):
        self._process_data = bool(value)

    def _check_usb_ports_availability(self):
        available_ports = self.available_ports_info()
        available_ports_names = {port.portName() for port in available_ports}
        last_port_names = {port.portName() for port in self._last_available_usb_ports}

        self._last_available_usb_ports = available_ports
        # print(available_ports_names, last_port_names, available_ports_names.union(last_port_names))
        
        if len(available_ports_names.union(last_port_names)) != len(last_port_names) or \
            len(available_ports_names.union(last_port_names)) != len(available_ports_names):
            self._view_form.update_ports()

    def setected_port_info(self):
        return None if self._reader is None else self._reader.port_info()
    
    def available_ports_info(self):
        return QSerialPortInfo.availablePorts()

    def setup_glasses_reader(self, port_info: QSerialPortInfo):
        self._reader = GlassesReader(port_info=port_info)
        self._reader.started.connect(self._glasses_reader_started)
        self._reader.data_changed.connect(self._glasses_reader_data_changed)
        self._reader.finished.connect(self._glasses_reader_finished)
        self._reader.error_occured.connect(self._glasses_reader_error)
        self._reader.open()

    @pyqtSlot()
    def _glasses_reader_started(self):
        self._view_form.set_experiment_runnable(True)
        self._view_form.set_glasses_running(True)
    
    @pyqtSlot()
    def _glasses_reader_finished(self):
        self._view_form.set_experiment_runnable(False)
        self._view_form.set_glasses_running(False)
        if self.is_experiment_running():
            self.stop_clicked()

    @pyqtSlot(np.ndarray)
    def _glasses_reader_data_changed(self, data:np.ndarray):
        if not self._process_data:
            return
        
        self._recieve_data_ind += 1
        
        
        if self._glasses_calib_result is not None:
            model = self._glasses_calib_result.model
            pos = model.predict(data.reshape(1, NUM_SENSORS))[0]
            if self._recieve_data_ind % 2 != 0:
                if self._current_running_config is not None and self._current_running_config.show_cursor:
                    self._commands_controller.set_cursor_center(QPointF(pos[0], pos[1]))
                else:
                    self._commands_controller.set_cursor_center(None)

        com_ind, com = self._commands_controller.grid_commands_generator().current_target()
        if com is not None:
            com_code = com.code
            x_rel = com.x_rel
            y_rel = com.y_rel
            pix = self._commands_controller.get_command_position(com)
            x_pix = pix.x()
            y_pix = pix.y()
            
        else:
            com_code = None
            x_rel = None
            y_rel = None
            x_pix = None
            y_pix = None

        if self._making_command:
            match self._state:
                case ControllerState.FREE_RUN:
                    return
                case ControllerState.RUNNING_CALLIBRATION:
                    if self._glasses_calibration_data_saver.is_writing_person_data():
                        self._glasses_calibration_data_saver.append_data(com_ind,
                                                                        com_code,
                                                                        [x_rel, y_rel],
                                                                        [x_pix, y_pix],
                                                                        data)
                        if x_pix is not None:
                            self._callibrator.add_callibration_data(com.code, [x_pix, y_pix], data)
                case ControllerState.RUNNING_EXPERIMENT:
                    predicted_pix = self._glasses_calib_result.model.predict(data.reshape(-1, NUM_SENSORS))[0]
                    predicted_point = QPointF(predicted_pix[0], predicted_pix[1])

                    best_match_command = self._commands_controller.best_match_command(predicted_point)
                    best_match_command_code = best_match_command.code
                    best_match_command_pos = self._commands_controller.get_command_position(best_match_command)
                    best_match_command_pos = best_match_command_pos.x(), best_match_command_pos.y()

                    # print('best match command', best_match_command, best_match_command_code)
                    self._experiment_control.add_best_match_command(best_match_command_code)
            
                    self._glasses_experiment_data_saver.append_data(com_ind,
                                                                    com_code,
                                                                    [x_rel, y_rel],
                                                                    [x_pix, y_pix],
                                                                    data,
                                                                    best_match_command_code,
                                                                    best_match_command_pos,
                                                                    predicted_pix)
                
    @pyqtSlot()
    def _glasses_reader_finished(self):
        self._view_form.set_experiment_running(False)
        self._view_form.set_experiment_runnable(False)
    
    @pyqtSlot(str)
    def _glasses_reader_error(self, error_str: str):
        self._view_form.show_glasses_error(error_str)

    def start_callibrate(self, experiment_config: CurrentConfig):
        # todo make form run only stop button and close
        target_size_pix = self._drawer.drawing_surface_size()
        view_size = self._drawer.view_size()
        
        self._commands_controller.set_grid_commands_generator(CallibrationGridGenerator(9))
        self._state = ControllerState.RUNNING_CALLIBRATION
        self._experiment_control.start(replace(experiment_config, num_commands=self._commands_controller.grid_commands_generator().max_commands()))

        self._last_calibration_id = str(uuid4())
        self._glasses_calibration_data_saver = GlassesCallibrationDataSaver(experiment_config.save_path)
        self._glasses_calibration_data_saver.create_person_dataset(
                                              self._last_calibration_id,
                                              '',
                                              False,
                                              experiment_config.num_commands,
                                              experiment_config.command_time,
                                              target_size_pix.width(),
                                              target_size_pix.height(),
                                              view_size.width(),
                                              view_size.height())
        self._callibrator = GlassesCallibrator()
        self._callibrator.start_callibrate()

    def stop_callibrate(self, early_stop=False):
        if self._glasses_calibration_data_saver is None:
            return
        if not self._glasses_calibration_data_saver.is_writing_person_data():
            return
        if early_stop:
            self._glasses_calibration_data_saver.delete_current_record()
            self._view_form.set_experiment_running(False)
            self._state = ControllerState.FREE_RUN
            return
        
        self._glasses_calib_result = model_result = self._callibrator.generate_model()
        self._glasses_calibration_data_saver.add_callibration_result(model_result)
        self._glasses_calibration_data_saver.stop_save(False)

        # todo allow form to run experiment
        self._state = ControllerState.FREE_RUN

    def start_experiment(self, experiment_config: CurrentConfig):
        print('start experiment')
        if self._last_calibration_id is None:
            return
        # todo make form run only stop button and close
        self._state = ControllerState.RUNNING_EXPERIMENT
        print(experiment_config)

        self._experiment_control.start(experiment_config)
        self._commands_controller.set_grid_commands_generator(GridCommandsGenerator(experiment_config.num_commands))

        target_size_pix = self._drawer.drawing_surface_size()
        view_size = self._drawer.view_size()
        self._glasses_experiment_data_saver = GlassesDataSaver(experiment_config.save_path)
        self._glasses_experiment_data_saver.create_person_dataset(experiment_config.person_name,
                                              experiment_config.test_id,
                                              experiment_config.show_cursor,
                                              experiment_config.num_commands,
                                              experiment_config.command_time,
                                              target_size_pix.width(),
                                              target_size_pix.height(),
                                              view_size.width(),
                                              view_size.height(),
                                              self._last_calibration_id)
        
    
    def is_experiment_running(self):
        if self._glasses_experiment_data_saver is not None and\
            self._glasses_experiment_data_saver.is_writing_person_data():
            return True
        return False

    def stop_experiment(self, early_stop: bool=False, do_save_if_early=False):
        if self._glasses_experiment_data_saver is not None and\
            self._glasses_experiment_data_saver.is_writing_person_data():
            if not do_save_if_early and early_stop:
                self._glasses_experiment_data_saver.delete_current_record()
            else:
                self._glasses_experiment_data_saver.stop_save(early_stop=early_stop)
                
        # todo allow form to run other stuff
        self._state = ControllerState.FREE_RUN
    
    def start_clicked(self):
        print('start clicked')
        if self._reader is None:
            self._view_form.show_glasses_not_set()
            return

        if not self._reader.is_correct():
            self._view_form.show_glasses_not_set()
            return
        
        self.start_experiment(self._view_form.experiment_config())

    def callibrate_clicked(self):
        if self._reader is None:
            self._view_form.show_glasses_not_set()
            return

        if not self._reader.is_correct():
            self._view_form.show_glasses_not_set()
            return
        
        self.start_callibrate(self._view_form.experiment_config())

    def stop_clicked(self):
        self._experiment_control.interrupt()
    
    def close(self):
        if self._reader is None:
            return
        if self._reader.is_running():
            self.stop_clicked()
            self._reader.close()
        self._drawer.close()
        


class GlassesTrackerExperiment(QMainWindow):
    window_closing = pyqtSignal(CurrentConfig)
    def __init__(self, cached_config: CurrentConfig,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setup_ui()
        self._closing = False

        self._drawer = GridExperimentDrawer(QSize(1920, 1080))
        self._drawer.resize(800, 600)    
        self._drawer.setWindowFlags(Qt.WindowType.WindowMaximizeButtonHint)
        self._drawer.show()
        
        self.activateWindow()

        self._commands_controller = GridCommandsController()
        self._commands_controller.set_drawer(self._drawer)
        self._commands_controller.set_grid_commands_generator(self._create_commands_generator(0))

        self._controller = GlassesController(self._drawer,
                                             self._commands_controller,
                                             self)
        self._ui.config.restore_experiment_config(cached_config)
        self._ui.config._ui.num_commands.valueChanged.connect(self.set_num_commands)
        self.set_num_commands(cached_config.num_commands)
        self._ui.config._ui.show_cursor.toggled.connect(self.set_show_cursor)
        self.set_show_cursor(cached_config.show_cursor)

        # self._ui.start_btn.clicked.connect(lambda: self._controller.start_experiment(self._ui.config.experiment_config()))
        # self._ui.calibrate_btn.clicked.connect(lambda: self._controller.start_callibrate(self._ui.config.experiment_config()))
        self._ui.start_btn.clicked.connect(self._controller.start_clicked)
        self._ui.calibrate_btn.clicked.connect(self._controller.callibrate_clicked)
        self._ui.stop_btn.clicked.connect(self._stop_clicked)

        self._usb_devices_group = QActionGroup(self)
        self._usb_devices_group.setExclusive(True)
        self._usb_devices_group.triggered.connect(self._port_selected)
        

    def show_finish_experiment_msg_and_ask_if_to_save_data(self) -> bool:
        QApplication.beep()
        self.mb = QMessageBox()
        self.mb.setWindowTitle('Внимание')
        self.mb.setText('Эксперимент завершен заранее. Сохранить данные эксперимента?')
        self.mb.setIcon(QMessageBox.Icon.Warning)
        self.mb.setStandardButtons(QMessageBox.StandardButton.Yes)
        self.mb.addButton(QMessageBox.StandardButton.No)
        self.mb.setDefaultButton(QMessageBox.StandardButton.No)
        return self.mb.exec() == QMessageBox.StandardButton.Yes

    def show_finish_experiment_msg_and_data_is_not_saved(self):
        QApplication.beep()
        self.mb = QMessageBox()
        self.mb.setWindowTitle('Внимание')
        self.mb.setText('Эксперимент завершен заранее. Данные не будут сохранены')
        self.mb.setIcon(QMessageBox.Icon.Warning)
        self.mb.exec()

    def show_finish_experiment_msg(self, num_executed, total_commands):
        QApplication.beep()
        self.mb = QMessageBox()
        self.mb.setIcon(QMessageBox.Icon.Information)
        self.mb.setWindowTitle('Готово')
        self.mb.setText(f'Эксперимент завершен\n{num_executed} / {total_commands}')
        self.mb.exec()

    def show_glasses_not_set(self):
        QApplication.beep()
        self.mb = QMessageBox()
        self.mb.setWindowTitle('Внимание')
        self.mb.setText('Сначала произведите настройку очков')
        self.mb.setIcon(QMessageBox.Icon.Critical)
        self.mb.exec()

    @pyqtSlot()
    def _stop_clicked(self):
        self._controller.stop_clicked()

    def update_ports(self):
        self._ui.menu.clear()
        print('update_ports')
        selected_port_info = self._controller.setected_port_info()
        available_ports = self._controller.available_ports_info()

        for port in available_ports:
            act = QAction(port.portName(), self._usb_devices_group)
            act.setCheckable(True)
            act.setData(port)

            if selected_port_info is not None and selected_port_info == port:
                act.setChecked(True)

            self._ui.menu.addAction(act)
        
    def _port_selected(self, action: QAction):
        print(action, action.data(), action.text())
        port_info = action.data()
        self._controller.setup_glasses_reader(port_info)

    def set_num_executed_commands(self, num_commands: int):
        self._ui.progressBar.setValue(num_commands+1)
    
    def set_num_commands(self, num_command: int):
        self._ui.progressBar.setMaximum(num_command)
    
    def set_show_cursor(self, do_show):
        print('def set_show_cursor(self, do_show):', do_show)
        self._commands_controller.set_show_best_match_command(do_show)
        self._commands_controller.set_show_cursor(do_show)
        self._controller._current_running_config = self.experiment_config()

    def set_experiment_runnable(self, runnable: bool):
        return
        self._ui.experiment_controls.setEnabled(runnable)
    
    def set_glasses_running(self, running: bool):
        if running:
            self._ui.statusbar.showMessage('Очки подключены')
        else:
            self._ui.statusbar.showMessage('Очки отключены')

    def show_glasses_error(self, err_str):
        self.mb = QMessageBox()
        self.mb.setIcon(QMessageBox.Icon.Critical)
        self.mb.setWindowTitle('Ошибка очков')
        self.mb.setText(str(err_str))
        self.mb.show()

    def set_experiment_running(self, running: bool):
        if self._closing:
            return
        
        self._ui.start_btn.setEnabled(not running)
        self._ui.calibrate_btn.setEnabled(not running)
        self._ui.stop_btn.setEnabled(running)
        self._ui.menu.setEnabled(not running)
        if running:
            # self._drawer.hide()
            self._drawer.showFullScreen()
            self._drawer.activateWindow()
        else:
            # self._drawer.hide()
            self._drawer.showNormal()
            self.activateWindow()
    
    def setup_ui(self):
        self._ui = Ui_GlassesTrackerExperiment()
        self._ui.setupUi(self)

    def _create_commands_generator(self, num_commands):
        return GridCommandsGenerator(num_commands)
    
    def experiment_config(self):
        return self._ui.config.experiment_config()
    
    def closeEvent(self, a0) -> None:
        self._closing = True
        self._controller.close()
        self.window_closing.emit(self._ui.config.experiment_config())
        self._drawer.close()
        return super().closeEvent(a0)
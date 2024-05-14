import typing
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import pyqtSlot
from glasses_tracker_experiment import GlassesTrackerExperiment
from hand_tracker_experiment import HandTrackerExperiment

from forms.select_video_input_window import SelectVideoInputWindow
from .ui_ExperimentsMainWidget import Ui_ExperimentsMainWidget
from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtMultimedia import QMediaDevices, QCameraDevice, QCamera, QVideoFrame
from head_tracker_experiment import HeadTrackerExperiment
from utils.camera_source import CameraSource
from utils.experiment_configs_model import CurrentConfig, ExperimentConfigsModel
# from 

class ExperimentsMainWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setup_ui()
        
        self.devices = QMediaDevices()
        self.devices.videoInputsChanged.connect(self._video_inputs_changed)
        self.camera_source: CameraSource = None
        
        self.select_video_input: SelectVideoInputWindow = None
        self.head_experiment_window: HeadTrackerExperiment = None
        self.hand_experiment_window: HandTrackerExperiment = None
        self.glasses_experiment_window: GlassesTrackerExperiment = None
        self.experiment_config_tracker = ExperimentConfigsModel(self)
        self.experiment_config_tracker.restore_from_file()

        self._ui.cam_select_btn.clicked.connect(self._open_camera_select)
        self._ui.head_experiment_btn.clicked.connect(self._open_head_experiment)
        self._ui.hands_experiment_btn.clicked.connect(self._open_hands_experiment)
        self._ui.glasses_experiment_btn.clicked.connect(self._open_glasses_experiment)

        
        self._ui.configure_experiment_widget.restore_experiment_config(self.experiment_config_tracker.config())

    def setup_ui(self):
        self._ui = Ui_ExperimentsMainWidget()
        self._ui.setupUi(self)

    @pyqtSlot()
    def _video_inputs_changed(self):
        can_use_camera = len(QMediaDevices.videoInputs()) > 0
        self._ui.hands_experiment_btn.setEnabled(can_use_camera)
        self._ui.head_experiment_btn.setEnabled(can_use_camera)

    # Processing camera selection window
    @pyqtSlot()
    def _open_camera_select(self):
        if self.camera_source is not None:
            self.camera_source.stop()
            self.camera_source = None
        self.select_video_input = SelectVideoInputWindow()
        # self.select_video_input.camera_selected.connect(self._camera_selected)
        self.select_video_input.camera_source_selected.connect(self._camera_source_selected)
        self.select_video_input.window_closing.connect(self._camera_select_closing)

        self.select_video_input.show()
        self.hide()
        self.select_video_input.window_closing.connect(self.show)

    # @pyqtSlot(QCameraDevice, QVideoFrame.RotationAngle, bool)
    # def _camera_selected(self, camera_device: QCameraDevice, rotation: QVideoFrame.RotationAngle, id_mirrored: bool):
    #     self.camera_source = CameraSource(camera_device, self)
    #     self.camera_source.set_rotation_angle(rotation)
    #     self.camera_source.set_mirrored(id_mirrored)
    #     self.camera_source.start()
    #     self.camera_source.camera.errorOccurred.connect(self._show_camera_error)
    #     # self.camera_source.suspend()

    @pyqtSlot(CameraSource)
    def _camera_source_selected(self, camera_source: CameraSource):
        self.camera_source = camera_source
        print('camera selected')

    # Processing expriments' windows

    def _check_and_warn_if_camera_not_selected(self):
        if self.camera_source is None:
            mb = QMessageBox()
            mb.setIcon(QMessageBox.Icon.Critical)
            mb.setWindowTitle('Доступ закрыт')
            mb.setText('Обратите внимание')
            mb.setInformativeText('Функция не доступна, пока не проведена настройка камеры')
            mb.exec()
            return False
        
        if not self.camera_source.camera.isAvailable():
            mb = QMessageBox()
            mb.setIcon(QMessageBox.Icon.Critical)
            mb.setInformativeText('Выбранная камера не доступна')
            mb.exec()
            return False
        
        return True

    @pyqtSlot()
    def _open_head_experiment(self):
        if not self._check_and_warn_if_camera_not_selected():
            return
        
        self.experiment_config_tracker.set_config(self._ui.configure_experiment_widget.experiment_config())

        self.head_experiment_window = HeadTrackerExperiment(self.camera_source,
                                                            self.experiment_config_tracker.config())
        self.head_experiment_window.show()
        self.hide()
        self.head_experiment_window.window_closing.connect(self._process_experiment_close)

    @pyqtSlot()
    def _open_hands_experiment(self):
        if not self._check_and_warn_if_camera_not_selected():
            return
        
        self.experiment_config_tracker.set_config(self._ui.configure_experiment_widget.experiment_config())

        self.hand_experiment_window = HandTrackerExperiment(self.camera_source,
                                                            self.experiment_config_tracker.config())
        self.hand_experiment_window.show()
        self.hide()
        self.hand_experiment_window.window_closing.connect(self._process_experiment_close)
        

    @pyqtSlot()
    def _open_glasses_experiment(self):
        self.experiment_config_tracker.set_config(self._ui.configure_experiment_widget.experiment_config())

        self.glasses_experiment_window = GlassesTrackerExperiment(self.experiment_config_tracker.config())
        self.glasses_experiment_window.show()
        self.hide()
        self.glasses_experiment_window.window_closing.connect(self._process_experiment_close)

    @pyqtSlot(CurrentConfig)
    def _process_experiment_close(self, experiment_config: CurrentConfig):
        self.experiment_config_tracker.set_config(experiment_config)
        self._ui.configure_experiment_widget.restore_experiment_config(experiment_config)
        self.show()
    
    # closing windows processing
    @pyqtSlot()
    def _camera_select_closing(self):
        self.select_video_input = None
    
    def closeEvent(self, a0) -> None:
        if self.camera_source is not None:
            self.camera_source.stop()
        self.experiment_config_tracker.set_config(self._ui.configure_experiment_widget.experiment_config())
        self.experiment_config_tracker.save_to_file()
        return super().closeEvent(a0)

    # error messages
    def _show_camera_error(self):
        if self.camera_source.camera.error() != QCamera.Error.NoError:
            QMessageBox.warning(self, 'Ошибка камеры', self.camera_source.camera.errorString())
            print('some err', self.camera_source.camera.error())
            self.camera_source.stop()
            self.camera_source = None



    
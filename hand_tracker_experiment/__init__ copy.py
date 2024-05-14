import typing
from PyQt6 import QtCore
import cv2, time
import numpy as np
from experiments_common.grid_experiment_drawer import GridExperimentDrawer
from experiments_common.grid_commands_generator import GridCommandsGenerator, GridCommand
from hand_tracker_experiment.hand_data_saver import HandDataSaver
from hand_tracker_experiment.ui_HandTrackerExperiment import Ui_HandTrackerExperiment
from utils.camera_source import CameraSource, convert_cv_qimage, convert_qimage_cv, convert_qpixmap_cv
from forms.configure_experiment_widget import ConfigureExperimentWidget
from utils.experiment_configs_model import CurrentConfig
from forms.experiment_control_widget import ExperimentControlWidget
from utils.threading import Worker
from .draw_hand_landmarks import draw_landmarks_on_image
from dataclasses import dataclass

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from PyQt6.QtMultimedia import QImageCapture, QVideoFrame
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox, QSizePolicy
from PyQt6.QtCore import pyqtSlot, pyqtSignal, QTimer, QThreadPool, QPointF, Qt
from PyQt6.QtGui import QPixmap, QImage, QPalette, QColor
from pathlib import Path



FINGERS_TIPS = {
  'THUMB': 4,
  'INDEX': 8,
  'MIDDLE': 12,
  'RING': 16,
  'PINKY': 20
}

@dataclass(frozen=True)
class HandScanResults:
    detection_results : object
    finger_tip: np.ndarray
    raw_image: np.ndarray
    hand_visible: bool


class HandTrackerExperiment(QWidget):
    window_closing = pyqtSignal()
    def __init__(self,  camera_source: CameraSource, cached_config: CurrentConfig, parent=None) -> None:
        super().__init__(parent)
        self.setup_ui()

        base_options = python.BaseOptions(model_asset_path=str(Path(__file__).parent / 'hand_landmarker.task'))
        options = vision.HandLandmarkerOptions(base_options=base_options,
                                            num_hands=1)
        from mediapipe.tasks.python.vision.core import vision_task_running_mode
        run_video_mode = vision_task_running_mode.VisionTaskRunningMode.VIDEO
        self.detector = vision.HandLandmarker.create_from_options(base_options=options,
                                                                  running_mode=run_video_mode)

        self.camera_source = camera_source
        self._closing = False
        self._show_captured_image_only = False
        self.worker: Worker = None
        self._hand_scan_results: HandScanResults = None

        self._commands_index = 0

        
        self._data_saver:HandDataSaver = None
        self.thread_pool = QThreadPool()

        self.drawer = GridExperimentDrawer()
        self.drawer.resize(800, 600)    
        self.drawer.setWindowFlags(Qt.WindowType.WindowMaximizeButtonHint)
        
        self._default_palette_color = self.drawer.palette().color(QPalette.ColorRole.Window)
        self._hand_not_found_palette_color = QColor(Qt.GlobalColor.red)


        self._ui.controls._ui.configs._ui.show_cursor.toggled.connect(self._show_cursor_toggled)
        self._ui.capture_base_image_btn.clicked.connect(self._update_captured_image)
        self._update_captured_image()
        self._show_cursor_toggled(cached_config.show_cursor)

        self._ui.controls.set_config(cached_config)

        self._ui.controls.started.connect(self._start_experiment)
        self._ui.controls.progressed.connect(self._progress_experiment)
        self._ui.controls.finished.connect(self.stop_experiment)

        self._ui.default_image.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)

        self.camera_source.frame_captured.connect(self._process_frame_image)
        
        self.drawer.set_commands_generator(self._create_commands_generator(0))
        self.drawer.show()
        self.activateWindow()

    def _create_commands_generator(self, n_commands=0):
        return GridCommandsGenerator(n_commands, offset_b=0.3, offset_r=0.3)

    def setup_ui(self):
        self._ui = Ui_HandTrackerExperiment()
        self._ui.setupUi(self)
    
    @pyqtSlot(bool)
    def _show_cursor_toggled(self, do_show):
        self._show_captured_image_only = not do_show
        self.show_static_image_if_required()

    def show_static_image_if_required(self):
        if self._show_captured_image_only:
            self.drawer.set_base_image(self._captured_image)

    @pyqtSlot()
    def _update_captured_image(self):
        self._captured_image = QImage(self.camera_source.video_frame().toImage())
        self._ui.default_image.setPixmap(QPixmap.fromImage(self._captured_image))
        self.show_static_image_if_required()

    @pyqtSlot(QVideoFrame, int)
    def _process_frame_image(self, frame: QVideoFrame, timestamp: int):
        if self._closing: return
        if self.worker is not None:
            if not self.worker.is_finished:
                return
        img = frame.toImage()
        frame = cv2.cvtColor(convert_qimage_cv(img), cv2.COLOR_RGBA2RGB)
        self.worker = Worker(self.do_scan, frame, timestamp)
        self.worker.signals.result.connect(self._after_scan)
        self.thread_pool.start(self.worker)

    def do_scan(self, frame: np.ndarray, timestamp: int):
        detection_result = self.detector.detect_for_video(mp.Image(mp.ImageFormat.SRGB, frame), timestamp)
        if len(detection_result.hand_landmarks):
            height, width, _ = frame.shape
            for i in range(len(detection_result.hand_landmarks)):
                landmark = detection_result.hand_landmarks[i][FINGERS_TIPS['INDEX']]
                # landmark_world = detection_result.hand_world_landmarks[i][FINGERS_TIPS['INDEX']]
                # print(landmark_world.z)
                x, y = landmark.x * width, landmark.y * height
                
                hand_scan_results = HandScanResults(detection_result,
                                                         (x, y),
                                                         frame,
                                                         True)
                break
            else:
                hand_scan_results = HandScanResults(None, None, frame, False)
        else:
            hand_scan_results = HandScanResults(None, None, frame, False)
        
        return hand_scan_results
        
        
    def _after_scan(self, hand_scan_results: HandScanResults):
        frame = hand_scan_results.raw_image

        palette = self.drawer.palette()
        current_color = palette.color(QPalette.ColorRole.Window)    
        if hand_scan_results.hand_visible:
            if current_color != self._default_palette_color:
                palette.setColor(QPalette.ColorRole.Window, self._default_palette_color)
                self.drawer.setPalette(palette)
        else:
            if current_color != self._hand_not_found_palette_color:
                palette.setColor(QPalette.ColorRole.Window, self._hand_not_found_palette_color)
                self.drawer.setPalette(palette)

        if hand_scan_results.hand_visible and not self._show_captured_image_only:
            frame = draw_landmarks_on_image(frame, hand_scan_results.detection_results)

            self.drawer.set_cursor_center(QPointF(hand_scan_results.finger_tip[0],
                                                  hand_scan_results.finger_tip[1]))
        else:
            self.drawer.set_cursor_center(None)
        if not self._show_captured_image_only:
            self.drawer.set_base_image(convert_cv_qimage(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)))
        # else:
        #     self.render_window.set_base_cvimage(self._captured_image)


        if hand_scan_results.hand_visible:
            landmarks = [(landmark.x, landmark.y, landmark.z) for landmark in hand_scan_results.detection_results.hand_landmarks[0]]
            world_landmarks = [(landmark.x, landmark.y, landmark.z) for landmark in hand_scan_results.detection_results.hand_world_landmarks[0]]
        else:
            landmarks = None
            world_landmarks = None
        

        command_ind, current_command = self._commands_generator.current_target()
        if current_command is not None:
            size = self.drawer.drawing_surface_size()
            command_code = current_command.code

            target_rel = current_command.x_rel, current_command.y_rel
            target_pix = target_rel[0] * size.width(), target_rel[1] * size.height()
        else:
            target_rel = None
            target_pix = None

        if self._data_saver is not None and self._data_saver.is_writing_person_data():
            self._data_saver.append_data(command_ind, command_code, target_rel, target_pix, landmarks, world_landmarks)


    @pyqtSlot(CurrentConfig)
    def _start_experiment(self, experiment_config: CurrentConfig):
        save_path_dir = experiment_config.save_path.parent
        if not save_path_dir.exists():
            save_path_dir.mkdir()
        
        self._commands_generator = self._create_commands_generator(experiment_config.num_commands)
        self._commands_index = 0

        target_size_pix = self.drawer.drawing_surface_size()
        self._data_saver = HandDataSaver(experiment_config.save_path)
        self._data_saver.create_person_dataset(experiment_config.person_name,
                                              experiment_config.test_id,
                                              experiment_config.show_cursor,
                                              experiment_config.num_commands,
                                              experiment_config.command_time,
                                              target_size_pix.width(),
                                              target_size_pix.height()
                                              )
        self._data_saver.save_preview_image(convert_qimage_cv(self._captured_image))
        self.drawer.set_commands_generator(self._commands_generator)

    @pyqtSlot(int, int)
    def _progress_experiment(self, command_ind, max_commands):
        self._commands_index = command_ind
        self._commands_generator.update_command_ind()

    @pyqtSlot(bool)
    def stop_experiment(self, early_stop):
        QApplication.beep()
        if early_stop:
            self.mb = QMessageBox()
            self.mb.setWindowTitle('Внимание')
            self.mb.setText('Эксперимент завершен заранее')
            self.mb.setIcon(QMessageBox.Icon.Warning)
            self.mb.setStandardButtons(QMessageBox.StandardButton.Yes)
            self.mb.addButton(QMessageBox.StandardButton.No)
            self.mb.setDefaultButton(QMessageBox.StandardButton.No)
            if self.mb.exec() == QMessageBox.StandardButton.Yes:
                self._data_saver.stop_save(True)
            else:
                self._data_saver.delete_current_record()
        else:
            self._data_saver.stop_save(early_stop)
            self.mb = QMessageBox()
            self.mb.setIcon(QMessageBox.Icon.Information)
            self.mb.setWindowTitle('Готово')
            self.mb.setText('Эксперимент завершен')
            self.mb.exec()

    def closeEvent(self, a0) -> None:
        self._closing = True

        if self._data_saver is not None and self._data_saver.is_writing_person_data():
            self._stop_experiment(True)
        
        self.drawer.close()
        
        self.thread_pool.waitForDone()
        self.window_closing.emit()
        return super().closeEvent(a0)
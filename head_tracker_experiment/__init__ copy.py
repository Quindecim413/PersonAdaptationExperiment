from PyQt6 import QtGui
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QApplication, QDialogButtonBox
from experiments_common.grid_experiment_drawer import GridExperimentDrawer
from experiments_common.grid_commands_generator import GridCommandsGenerator
from head_tracker_experiment.head_data_saver import HeadDataSaver
from core.virtual_camera import VirtualCamera

from .processing.head_scanner import HeadScanResults, HeadScanner
from utils.threading import Worker
from .commands_drawer import CommandsDrawer
from .ui_HeadTrackerExperiment import Ui_HeadTrackerExperiment
from core.scene import Scene
from .head_model import HeadModel
from obj_models import LabStend
from utils.camera_source import CameraSource, convert_qpixmap_cv, convert_cv_qpixmap, convert_qimage_cv, convert_cv_qimage
from utils.experiment_configs_model import CurrentConfig
from PyQt6.QtGui import QImage, QPixmap, QPalette, QColor
from PyQt6.QtCore import pyqtSlot, pyqtSignal, QTimer, QThreadPool, Qt, QPointF
from PyQt6.QtMultimedia import QVideoFrame
from forms.label_image import LabelImage
import numpy as np, cv2, time


class TrackHeadMovementsWindow(QWidget):
    def __init__(self, lab_stend: LabStend) -> None:
        super().__init__()
        self.lab_stend = lab_stend
        self.commands_tracker = CommandsDrawer(self.lab_stend)
        self.setup_ui()

        self.show_intersection = True

        self._update_timer = QTimer(self)
        self._update_timer.setInterval(int(1000/20))
        self._update_timer.timeout.connect(self.update_view)
        self._update_timer.start()

    def set_intersection(self, intersection):
        self.intersection = intersection

        if self.show_intersection:
            self.commands_tracker.update_intersection(self.intersection)
        else:
            self.commands_tracker.update_intersection(None)

    def set_target_rel(self, target_relative):
        self.commands_tracker.update_target_relative(target_relative)

    def update_view(self):
        self.commands_tracker.update_view()
        self.render_preview.setCVImage(self.commands_tracker.image)

    def setup_ui(self):
        self.render_preview = LabelImage()
        vbox = QVBoxLayout()
        vbox.addWidget(self.render_preview)
        self.setLayout(vbox)


class HeadTrackerExperiment(QWidget):
    window_closing = pyqtSignal()
    def __init__(self, camera_source: CameraSource, cached_config: CurrentConfig, parent=None) -> None:
        super().__init__(parent)
        self.setup_ui()
        self._ui.controls._ui.configs._ui.show_cursor.toggled.connect(self._show_cursor_toggled)
        
        self._show_cursor = True
        self._commands_index = 0
        
        self._data_saver:HeadDataSaver = None
        self.thread_pool = QThreadPool()
        self._commands_generator = self._create_commands_generator(0)

        self.setup_scene()
        self._ui.controls.set_config(cached_config)
        self.camera_source = camera_source
        self.head_scanner = HeadScanner(True)

        self._ui.controls.started.connect(self._start_experiment)
        self._ui.controls.finished.connect(self._stop_experiment)
        self._ui.controls.progressed.connect(self._progress_experiment)


        self._closing = False
        self._data_saver = None
        self.worker: Worker = None
        self._scan_results: HeadScanResults = None

        self.thread_pool = QThreadPool()

        self.drawer = GridExperimentDrawer()
        self.drawer.resize(800, 600)    
        self.drawer.setWindowFlags(Qt.WindowType.WindowMaximizeButtonHint)

        self._default_palette_color = self.drawer.palette().color(QPalette.ColorRole.Window)
        self._head_not_found_palette_color = QColor(Qt.GlobalColor.red)
        self.camera_source.frame_captured[(QVideoFrame, int)].connect(self._process_frame_image)

        self.drawer.set_commands_generator(self._create_commands_generator(0))
        self.drawer.show()
        self.activateWindow()

        self.camera_source.frame_captured[(QVideoFrame, int)].connect(self._process_frame_image)

        self._show_cursor_toggled(cached_config.show_cursor)

    def _create_commands_generator(self, n_commands=0):
        return GridCommandsGenerator(n_commands)

    def _show_cursor_toggled(self, do_show):
        self._show_cursor = do_show
        if not do_show:
            self.drawer.set_cursor_center(None)

    def setup_ui(self):
        self._ui = Ui_HeadTrackerExperiment()
        self._ui.setupUi(self)
    
    @pyqtSlot(CurrentConfig)
    def _start_experiment(self, experiment_config: CurrentConfig):
        save_path_dir = experiment_config.save_path.parent
        if not save_path_dir.exists():
            save_path_dir.mkdir()
        
        self._commands_generator = self._create_commands_generator(experiment_config.num_commands)
        self._commands_index = 0
        
        target_size_pix = self.drawer.drawing_surface_size()
        self._data_saver = HeadDataSaver(experiment_config.save_path)
        self._data_saver.create_person_dataset(experiment_config.person_name,
                                              experiment_config.test_id,
                                              experiment_config.show_cursor,
                                              experiment_config.num_commands,
                                              experiment_config.command_time,
                                              target_size_pix.width(),
                                              target_size_pix.height()
                                              )
        self.drawer.set_commands_generator(self._commands_generator)

    @pyqtSlot(bool)
    def _stop_experiment(self, early_stop):
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

    @pyqtSlot(int, int)
    def _progress_experiment(self, command_ind, max_commands):
        self._commands_index = command_ind
        self._commands_generator.update_command_ind()

    def setup_scene(self):
        self.lab_stend = LabStend()
        self.lab_stend.transform.move(-self.lab_stend.transform.get_up()*0.2)# + self.lab_stend.transform.get_right()*0.2)
        self.head_model = HeadModel()
        
        self.virtual_camera = VirtualCamera()
        self.virtual_camera.transform.set_position(self.virtual_camera.transform.get_up()*0.0915 + \
                                                self.virtual_camera.transform.get_forward() * (-0.05) )
        self.virtual_camera.transform.rotate(self.virtual_camera.transform.get_up(), 180)
        print('self.virtual_camera.transform.get_forward(True)', self.virtual_camera.transform.get_forward(True))

        self.virtual_camera.bind_node(self.head_model)

        self.scene = Scene()
        self.scene.bind_node(self.lab_stend)
        self.scene.bind_node(self.virtual_camera)

    @pyqtSlot(QVideoFrame, int)
    def _process_frame_image(self, frame: QVideoFrame, timestamp):
        if self._closing: return
        if self.worker is not None:
            if not self.worker.is_finished:
                return
        img = frame.toImage()
        frame = cv2.cvtColor(convert_qimage_cv(img), cv2.COLOR_RGBA2RGB)
        self.worker = Worker(self.do_scan, frame, timestamp)
        self.worker.signals.result.connect(self._after_scan)
        self.thread_pool.start(self.worker)
    
    def do_scan(self, cv_image, timestamp):
        scan_results = self.head_scanner.process(cv_image, timestamp)
        return scan_results

    def _after_scan(self, scan_results: HeadScanResults):
        qimage = convert_cv_qimage(scan_results.processed_image)
        self._ui.video_widget.set_image_to_videowidget(qimage)

        if scan_results.head_visible:
            try:
                self.head_model._update_transform_matrix(scan_results.head2cam_transform_mat)
            except Exception as e:
                print(scan_results.head2cam_transform_mat)
                raise e
        else:
            self.head_model._update_head_not_visible()
        
        if scan_results.head_visible:
            head_matrix = self.head_model.transform.get_matrix(True)
            cast_result = self.scene.cast_rays_from_origin(self.head_model.transform.get_position(True), 
                                            [self.head_model.transform.get_forward(True)])
            if len(cast_result.nodes) == 1 and cast_result.nodes[0] == self.lab_stend:
                intersection_3d = cast_result.points_3d[0]
            else:
                intersection_3d = None
        else:
            head_matrix = None
            intersection_3d = None
            
        size = self.drawer.drawing_surface_size()
        width_pix, height_pix = size.width(), size.height()
        vertices = self.lab_stend.screen_vertices
        command_ind, target_command = self._commands_generator.current_target()
        if target_command is not None:
            command_code = target_command.code
            x, y = target_rel = target_command.x_rel, target_command.y_rel
            hor = vertices['ru'] - vertices['lu']
            vert = vertices['lb'] - vertices['lu']
            target_3d = vertices['lu'] + x * hor + y * vert
            px, py = target_command.x_rel * width_pix, target_command.y_rel * height_pix
            target_pix = [px. py]
        else:
            command_code = None
            target_rel = None
            target_pix = None
            target_3d = None
            

        if intersection_3d is not None:
            hit_vec = intersection_3d - vertices['lu']
            hor_vec = vertices['ru'] - vertices['lu']
            vert_vec = vertices['lb'] - vertices['lu']
            x = hor_vec @ hit_vec / np.dot(hor_vec, hor_vec)
            y = vert_vec @ hit_vec / np.dot(vert_vec, vert_vec)
            px, py = x * width_pix, y * height_pix
            
            intersetion_pix = [px, py]
            self.drawer.set_cursor_center(QPointF(px, py))
        else:
            intersetion_pix = None
            self.drawer.set_cursor_center(None)

        if self._data_saver is not None and self._data_saver.is_writing_person_data():
            self._data_saver.append_data(command_ind,
                                        command_code,
                                        target_rel,
                                        target_pix,
                                        target_3d,
                                        intersetion_pix,
                                        intersection_3d,
                                        head_matrix)
        
    def closeEvent(self, a0) -> None:
        self._closing = True
        if self._data_saver is not None and self._data_saver.is_writing_person_data():
            self._stop_experiment(True)
        
        self.drawer.close()
        self.thread_pool.waitForDone()
        self.window_closing.emit()
        return super().closeEvent(a0)
import typing
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import pyqtSlot, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication
from PyQt6.QtGui import QActionGroup, QAction

from utils.camera_source import CameraSource
try:
    from .ui_SelectVideoInputWindow import Ui_SelectVideoInputWindow
except ImportError:
    from ui_SelectVideoInputWindow import Ui_SelectVideoInputWindow
from PyQt6.QtMultimedia import (QAudioInput, QCamera, QCameraDevice,
                                  QImageCapture, QMediaCaptureSession,
                                  QMediaDevices, QMediaMetaData,
                                  QMediaRecorder, QVideoFrameFormat,
                                  QVideoSink, QVideoFrame)

# class SelectVideoInputWindow(QMainWindow):
#     camera_selected = pyqtSignal(QCameraDevice)
#     window_closing = pyqtSignal()

#     def __init__(self, ) -> None:
#         super().__init__()
#         self.setup_ui()

#         self.m_captureSession = QMediaCaptureSession()
#         self.m_devices = QMediaDevices()
#         self._video_devices_group = QActionGroup(self)
#         self.m_camera: QCamera = None
        
#         self.m_devices.videoInputsChanged.connect(self.update_cameras)
#         self.update_cameras()

#         self.set_camera(QMediaDevices.defaultVideoInput())

#         self._ui.action_confirm_select.triggered.connect(self._confirmed)

#     def setup_ui(self):
#         self._ui = Ui_SelectVideoInputWindow()
#         self._ui.setupUi(self)

#     @pyqtSlot()
#     def _confirmed(self):
#         if not self.m_camera.cameraDevice().isNull():
#             self.camera_selected.emit(self.m_camera.cameraDevice())
#             self.m_camera.stop()
#         self.close()

#     @pyqtSlot()
#     def update_cameras(self):
#         available_cameras = QMediaDevices.videoInputs()
        
#         for camera_device in available_cameras:
#             video_device_action = QAction(camera_device.description(), self._video_devices_group)
#             video_device_action.setCheckable(True)
#             video_device_action.setData(camera_device)

#             if camera_device == QMediaDevices.defaultVideoInput():
#                 video_device_action.setChecked(True)
#                 self.set_camera(camera_device)
            
#             self._ui.menu_devices.addAction(video_device_action)
    
#     @pyqtSlot(QCameraDevice)
#     def set_camera(self, camera_device):
#         # QVideoFrameFormat.imageFormatFromPixelFormat(frame.pixelFormat())
#         # print([str(QVideoFrameFormat.imageFormatFromPixelFormat(device.pixelFormat())) for device in camera_device.videoFormats()])
#         # print([str(device.pixelFormat()) for device in camera_device.videoFormats()])

#         self.m_camera = QCamera(camera_device)
#         self.m_captureSession.setCamera(self.m_camera)
#         self.m_captureSession.setVideoOutput(self._ui.video_widget)

#         # self.m_camera.errorOccurred.connect(self.displayCameraError)

#         self.m_camera.start()
        
#         # print(str(self.m_camera.cameraFormat().pixelFormat()))
        
#     @pyqtSlot()
#     def displayCameraError(self):
#         if self.m_camera.error() != QCamera.NoError:
#             QMessageBox.warning(self, "Camera Error",
#                                 self.m_camera.errorString())
    
#     def closeEvent(self, a0) -> None:
#         self.window_closing.emit()
#         if self.m_camera.isAvailable():
#             self.m_camera.stop()
#         return super().closeEvent(a0)
            
class SelectVideoInputWindow(QMainWindow):
    camera_selected = pyqtSignal(QCameraDevice, QVideoFrame.RotationAngle, bool)
    camera_source_selected = pyqtSignal(CameraSource)
    window_closing = pyqtSignal()

    def __init__(self, ) -> None:
        super().__init__()
        self.setup_ui()
        self.camera_source = CameraSource(QMediaDevices.defaultVideoInput())
        self.connection = self.camera_source.frame_captured.connect(self.frame_captured)

        # self.camera_source.frame_captured.connect(self._ui.video_widget.videoSink().setVideoFrame)

        self._devices = QMediaDevices()
        self._video_devices_group = QActionGroup(self)
        self._video_devices_group.setExclusive(True)
        self._video_devices_group.triggered.connect(self.set_camera_action)


        self._devices.videoInputsChanged.connect(self.update_cameras)
        self.update_cameras()

        self._ui.action_rotate_clockwise.triggered.connect(self.camera_source.rotate_clockwise)
        self._ui.action_rotate_counter_clockwise.triggered.connect(self.camera_source.rotate_counter_clockwise)
        self._ui.action_mirror.toggled.connect(self.camera_source.set_mirrored)

        self._ui.action_confirm_select.triggered.connect(self._confirmed)

    @pyqtSlot(QVideoFrame)
    def frame_captured(self, frame: QVideoFrame):
        self._ui.video_widget.videoSink().setVideoFrame(frame)

    def setup_ui(self):
        self._ui = Ui_SelectVideoInputWindow()
        self._ui.setupUi(self)

    # @pyqtSlot()
    # def _confirmed(self):
    #     if not self.camera_source.camera.cameraDevice().isNull():
    #         self.camera_source.stop()
    #         self.camera_selected.emit(self.camera_source.camera.cameraDevice(), 
    #                                   self.camera_source.rotation_angle(), 
    #                                   self.camera_source.is_mirrored())
    #     self.close()

    @pyqtSlot()
    def _confirmed(self):
        if not self.camera_source.camera.cameraDevice().isNull():
            self.camera_source_selected.emit(self.camera_source)
        self.close()

    @pyqtSlot()
    def update_cameras(self):
        available_cameras = QMediaDevices.videoInputs()
        self._ui.menu_devices.clear()
        for camera_device in available_cameras:
            video_device_action = QAction(camera_device.description(), self._video_devices_group)
            video_device_action.setCheckable(True)
            video_device_action.setData(camera_device)

            if camera_device == QMediaDevices.defaultVideoInput():
                video_device_action.setChecked(True)
                video_device_action.setData(camera_device)
                self.set_camera(camera_device)
            
            self._ui.menu_devices.addAction(video_device_action)
    
    def set_camera_action(self, action: QAction):
        self.set_camera(action.data())


    @pyqtSlot(QCameraDevice)
    def set_camera(self, camera_device):
        self.camera_source.set_camera(camera_device)
        self.camera_source.start()
        
    @pyqtSlot()
    def displayCameraError(self):
        if self.m_camera.error() != QCamera.NoError:
            QMessageBox.warning(self, "Camera Error",
                                self.m_camera.errorString())
    
    def closeEvent(self, a0) -> None:
        # self.camera_source.stop()
        self.disconnect(self.connection)
        self.window_closing.emit()
        return super().closeEvent(a0)
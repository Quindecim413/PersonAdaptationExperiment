# https://stackoverflow.com/questions/74212553/how-to-convert-qvideoframe-from-qcamera-to-qimage

import typing
# from  mn, QAW  import QVideoWidget
from PyQt6.QtMultimedia import QVideoSink, QMediaCaptureSession, QCameraDevice, QMediaPlayer, QCamera, QVideoFrame, QVideoFrameFormat,QCameraFormat, QImageCapture
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QByteArray, QBuffer, QSize
from PyQt6.QtGui import QPixmap, QImage
import cv2, numpy as np, sys
import time


def convert_cv_qimage(cv_img):
    """Convert from an opencv image to QPixmap"""
    rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_image.shape
    bytes_per_line = ch * w
    qimg = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    return qimg

def convert_qimage_cv(qimage: QImage):
    # https://stackoverflow.com/questions/45020672/convert-pyqt5-qpixmap-to-numpy-ndarray
    ## Get the size of the current pixmap
    size = qimage.size()
    h = size.width()
    w = size.height()

    ## Get the QImage Item and convert it to a byte string
    qbits = qimage.bits()
    qbits.setsize(qimage.sizeInBytes())

    byte_str = qbits.asstring()

    ## Using the np.frombuffer function to convert the byte string into an np array
    img = np.frombuffer(byte_str, dtype=np.uint8).reshape((w,h,4))
    img = img[:,:,:3].copy()
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    return img#[:, :, :3].copy()

def convert_cv_qpixmap(cv_img):

    
    # p = convert_to_Qt_format.scaled(self.disply_width, self.display_height, Qt.KeepAspectRatio)
    return QPixmap.fromImage(convert_cv_qimage(cv_img))

def convert_qpixmap_cv(pixmap: QPixmap):
    return convert_qimage_cv(pixmap.toImage())


def convert_qimage_qvideoframe(qimage: QImage):
    # https://stackoverflow.com/questions/71407367/how-to-convert-qimage-to-qvideoframe-so-i-would-set-it-as-frame-for-videosink-qt
    # https://stackoverflow.com/questions/75311549/pyqt6-how-can-i-write-bytes-to-memory-using-sip-voidptr

    # https://github.com/JSS95/araviq6/blob/9980e39914b802fd7716608d460b44b4a90b6e01/araviq6/array2qvideoframe.py#L91

    img = qimage.convertToFormat(QImage.Format.Format_RGBA8888).copy()

    frame_format = QVideoFrameFormat(img.size(), QVideoFrameFormat.pixelFormatFromImageFormat(QImage.Format.Format_RGBA8888))
    frame = QVideoFrame(frame_format)
    # print('str(qimage.format())', str(img.format()), str(frame_format))
    frame.map(QVideoFrame.MapMode.ReadOnly)
    
    ptr = frame.bits(0)
    ptr.setsize(img.sizeInBytes())
    
    qbits = img.bits()

    qbits.setsize(img.sizeInBytes())
    ptr[:] = qbits.asstring()
    time.time()

    frame.unmap()
    return frame

    # image = QImage()

    
    # QVideoFrame frame(QVideoFrameFormat(img.size(), QVideoFrameFormat::pixelFormatFromImageFormat(img.format()));
    # frame.map(QVideoFrame::ReadWrite);
    # memcpy(frame.bits(0), img.bits(), img.sizeInBytes());
    # frame.unmap();
    # m_videoSink->setVideoFrame(frame);


# https://stackoverflow.com/questions/73568982/qt-getting-a-thumbnail-for-a-video
class CameraSource(QObject):
    frame_captured = pyqtSignal((QVideoFrame,), (QVideoFrame, int)) # frame, timestamp(milliseconds)
    video_rotation_angle_changed = pyqtSignal(QVideoFrame.RotationAngle)
    error_ocured = pyqtSignal(str)

    def __init__(self, camera_device: QCameraDevice, parent=None) -> None:
        super().__init__(parent)
        self.capture_session = QMediaCaptureSession(self)
        self.video_sink = QVideoSink()
        self.capture_session.setVideoSink(self.video_sink)
        
        self.camera = QCamera(camera_device)
        self.capture_session.setCamera(self.camera)
        self.capture_session.videoSink().videoFrameChanged.connect(self._frame_changed)
        self.camera.errorOccurred.connect(self._error_registered)
        self.camera.errorChanged.connect(lambda: print('error changed', self.camera.error()))

        self._run_start = time.time()
        self._time_captured = time.time()
        self._video_frame = None
        self._do_mirror = False
        self._capture_rotation_angle = QVideoFrame.RotationAngle.Rotation0

    @pyqtSlot(QCamera.Error, str)
    def _error_registered(self, err: QCamera.Error, err_str: str):
        print('Camera err', err_str)
        if err != QCamera.Error.NoError:
            self.error_ocured.emit(err_str)

    def name(self):
        device = self.camera.cameraDevice()
        if device is not None:
            return device.description()
        return ''

    def rotate_clockwise(self):
        print('rotate_clockwise')
        match self._capture_rotation_angle :
            case QVideoFrame.RotationAngle.Rotation0:
                self.set_rotation_angle(QVideoFrame.RotationAngle.Rotation90)
            case QVideoFrame.RotationAngle.Rotation90:
                self.set_rotation_angle(QVideoFrame.RotationAngle.Rotation180)
            case QVideoFrame.RotationAngle.Rotation180:
                self.set_rotation_angle(QVideoFrame.RotationAngle.Rotation270)
            case QVideoFrame.RotationAngle.Rotation270:
                self.set_rotation_angle(QVideoFrame.RotationAngle.Rotation0)
    
    def rotate_counter_clockwise(self):
        print('rotate_counter_clockwise')
        match self._capture_rotation_angle :
            case QVideoFrame.RotationAngle.Rotation0:
                self.set_rotation_angle(QVideoFrame.RotationAngle.Rotation270)
            case QVideoFrame.RotationAngle.Rotation90:
                self.set_rotation_angle(QVideoFrame.RotationAngle.Rotation0)
            case QVideoFrame.RotationAngle.Rotation180:
                self.set_rotation_angle(QVideoFrame.RotationAngle.Rotation90)
            case QVideoFrame.RotationAngle.Rotation270:
                self.set_rotation_angle(QVideoFrame.RotationAngle.Rotation180)

    
    def set_mirrored(self, value: bool):
        self._do_mirror = value
    
    def is_mirrored(self):
        return self._do_mirror

    def set_camera(self, camera_device: QCameraDevice):
        if self.camera != None and self.camera.isAvailable():
            self.camera.stop()
        self.camera = QCamera(camera_device)
        self.capture_session.setCamera(self.camera)

    def video_frame_timestamp_ms(self) -> typing.Tuple[QVideoFrame|None, int]:
        return [self._video_frame, self.timestamp_ms()]
    
    def video_frame(self):
        return self._video_frame

    def timestamp_ms(self):
        return int((self._time_captured - self._run_start)*1000)

    def start(self):
        self._run_start = time.time()
        self.camera.start()

    def continue_(self):
        self._run_start = time.time()
        self.camera.setActive(True)

    def suspend(self):
        self.camera.setActive(False)
    
    def stop(self):
        print('self.camera.error() ', self.camera.error() )
        if self.camera.error() == QCamera.Error.NoError:
            try:
                if self.camera.isActive():
                    self.camera.stop()
                elif self.camera.isAvailable():
                    self.camera.stop()
            except:
                pass
        elif self.camera.error() == QCamera.Error.CameraError:
            self.camera.stop()
        
    def is_available(self):
        return self.camera.isAvailable()

    def is_running(self):
        return self.camera.isActive()
    
    def set_video_output(self, output):
        self.capture_session.setVideoOutput(output)

    def set_rotation_angle(self, rotation_angle: QVideoFrame.RotationAngle):
        assert isinstance(rotation_angle, QVideoFrame.RotationAngle)
        self._capture_rotation_angle = rotation_angle
        self.video_rotation_angle_changed.emit(self._capture_rotation_angle)
    
    def rotation_angle(self):
        return self._capture_rotation_angle

    @pyqtSlot(QVideoFrame)
    def _frame_changed(self, frame: QVideoFrame):
        frame.setMirrored(self._do_mirror)
        frame.setRotationAngle(self._capture_rotation_angle)
        self._time_captured = time.time()
        self._video_frame = QVideoFrame(frame)
        self.frame_captured.emit(self._video_frame)
        self.frame_captured[QVideoFrame, int].emit(self._video_frame, self.timestamp_ms())
    
        
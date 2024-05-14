from typing import Tuple
from PyQt6.QtWidgets import QWidget, QLabel, QSizePolicy
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import pyqtSlot, Qt, QSize
from PyQt6 import QtGui
import numpy as np
import cv2


def convert_cv_qt(cv_img):
    """Convert from an opencv image to QPixmap"""
    rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_image.shape
    bytes_per_line = ch * w
    convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
    # p = convert_to_Qt_format.scaled(self.disply_width, self.display_height, Qt.KeepAspectRatio)
    return QPixmap.fromImage(convert_to_Qt_format)


class LabelImage(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(False)
        # self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
    
    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        if self._pixmap is not None:
            self.setPixmapScaled(self._pixmap, a0.size())

    def setCVImage(self, cv_image: np.ndarray):
        self.setPixmap(convert_cv_qt(cv_image))

    def setPixmap(self, pixmap: QPixmap) -> None:
        self.setPixmapScaled(pixmap, self.size())

    def setPixmapScaled(self, pixmap: QPixmap, size: QSize):
        self._pixmap = pixmap
        
        self.pixmap_scaled = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio)
        
        return super().setPixmap(self.pixmap_scaled)

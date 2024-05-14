from core.geometry_node import GeometryNode
from PyQt6.QtCore import pyqtSlot
import numpy as np


class HeadModel(GeometryNode):
    @pyqtSlot()
    def _update_head_not_visible(self):
        self.set_visible(False)
        print('_update_head_not_visible')

    @pyqtSlot(np.ndarray, np.ndarray)
    def _update_transform(self, R, t):
        self.set_visible(True)
        self.transform.set_position(t)
        self.transform.set_rotation_mat(R)

    @pyqtSlot(np.ndarray)
    def _update_transform_matrix(self, mtx):
        self.set_visible(True)
        try:
            self.transform.set_matrix(mtx)
        except Exception as e:
            print("MTX", mtx)
            raise e
import numpy as np
from core.transform import Transform

from core.processing.face_geometry import PCF, get_metric_landmarks_of_refined
from .head_pose_estimation.service import UltraLightFaceDetection
from .head_pose_estimation.service import DepthFacialLandmarks, DenseFaceReconstruction
from .head_pose_estimation.service import pose as render_pose
from PyQt6.QtCore import QObject, pyqtSignal
import os
import cv2
from .reference_world import ref2dImagePoints, ref3DModel

class HeadScanner:
    def __init__(self, visualize=False) -> None:
        self._fd = UltraLightFaceDetection(os.path.join(os.path.dirname(__file__),"head_pose_estimation/weights/RFB-320.tflite"),
                                        conf_threshold=0.95)
        self._fa = DenseFaceReconstruction(os.path.join(os.path.dirname(__file__),"head_pose_estimation/weights/sparse_face.tflite"))
        self.face_detected = False
        self.visualize = visualize
        self._box_color = (200, 50, 0)

        self.camera_matrix =np.array([[1080.1,   0., 950.2],
                                [  0.,1080.15, 475.0],
                                [  0.,     0., 1.   ]])
        self.mdists = np.zeros((1, 4), dtype=float)
        self._face3dmodel = ref3DModel()
        self.R = np.identity(3)

    def process(self, frame: np.ndarray):
        # face detection
        boxes, scores = results = self._fd.inference(frame)
        # raw copy for reconstruction
        feed = frame.copy()
        self.face_detected = len(boxes) > 0 
        if self.face_detected:
            for landmarks, pose in self._fa.get_landmarks(feed, boxes[:1]):
                self.landmarks = landmarks
                self.pose = pose
                if self.R is None:
                    self.R = np.identity(3)
                rot = np.linalg.inv(pose[:3, :3])
                self.R = self.R * 0.5 + rot * 0.5
                self.t = pose[:3, 3]/100

                ref_2d_image_points = ref2dImagePoints(landmarks)
                success, rotationVector, translationVector = cv2.solvePnP(
                self._face3dmodel, ref_2d_image_points, self.camera_matrix, self.mdists)
                # print('Estimated translation', translationVector.ravel())
                
                if self.visualize:
                    # print('Drawing', self.t)
                    render_pose(feed, (landmarks, pose), tuple(self._box_color))
        else:
            self.R = None
            self.t = None
        return feed
    
    def is_head_visible(self):
        return self.R is not None
from typing import List, Tuple, Union
import cv2
import numpy as np
import time
from functools import reduce
from dataclasses import dataclass
from PyQt6.QtCore import QPointF
from dataclasses_json import dataclass_json, global_config

@dataclass_json
@dataclass
class ArucoMarker:
    id: int
    top_left: QPointF
    top_right: QPointF
    bottom_right: QPointF
    bottom_left: QPointF

global_config.encoders[QPointF] = lambda el: f'{el.x()} {el.y()}'
global_config.decoders[QPointF] = lambda str_: QPointF(*str_.split(' '))
    

class ArucoMarkersDetector:
    def __init__(self,
                 marker_color=[0, 255, 0]) -> None:
        self._markers:List[ArucoMarker] = []
        self._last_visible_ids = []
        self._marker_color = marker_color
        arucoDict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)
        arucoParams = cv2.aruco.DetectorParameters()
        self._aruco_detector = cv2.aruco.ArucoDetector(arucoDict, arucoParams)

    def detect(self, image):
        # self._last_visible_ids.clear()
        self._markers.clear()
        print(image.dtype)
        (corners, ids, rejected) = self._aruco_detector.detectMarkers(image[:, :, :3])

        now = time.time()
        if len(corners) > 0:
            for (markerCorner, markerID) in zip(corners, ids):
                # extract the marker corners (which are always returned in
                # top-left, top-right, bottom-right, and bottom-left order)
                corners = markerCorner.reshape((4, 2))
                (topLeft, topRight, bottomRight, bottomLeft) = corners
                # convert each of the (x, y)-coordinate pairs to integers
                topRight = (int(topRight[0]), int(topRight[1]))
                bottomRight = (int(bottomRight[0]), int(bottomRight[1]))
                bottomLeft = (int(bottomLeft[0]), int(bottomLeft[1]))
                topLeft = (int(topLeft[0]), int(topLeft[1]))
                self._markers.append(ArucoMarker(int(markerID), 
                                                 QPointF(*topLeft), 
                                                 QPointF(*topRight), 
                                                 QPointF(*bottomRight), 
                                                 QPointF(*bottomLeft)))
                
    def markers(self):
        return self._markers.copy()

    def draw_markers(self, image):
        for marker in self._markers:
            border_color = self._marker_color
            top_left = np.array([marker.top_left.x(), marker.top_left.y()], dtype=int)
            top_right = np.array([marker.top_right.x(), marker.top_right.y()], dtype=int)
            bottom_right = np.array([marker.bottom_right.x(), marker.bottom_right.y()], dtype=int)
            bottom_left = np.array([marker.bottom_left.x(), marker.bottom_left.y()], dtype=int)
            
            cv2.line(image, top_left, top_right, border_color, 2, cv2.LINE_AA)
            cv2.line(image, top_right, bottom_right, border_color, 2, cv2.LINE_AA)
            cv2.line(image, bottom_right, bottom_left, border_color, 2, cv2.LINE_AA)
            cv2.line(image, bottom_left, top_left, border_color, 2, cv2.LINE_AA)

            cX = int((top_left[0] + bottom_right[0]) / 2.0)
            cY = int((top_left[1] + bottom_right[1]) / 2.0)
            cv2.circle(image, (cX, cY), 4, (0, 0, 255), -1)
            # draw the ArUco marker ID on the image
            cv2.putText(image, str(marker.id),
                (top_left[0], top_left[1] - 15), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (0, 255, 0), 2)
        
        return image
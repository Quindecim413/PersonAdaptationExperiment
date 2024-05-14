import numpy as np
from core.transform import Transform

from .face_geometry import PCF, get_metric_landmarks_of_refined
import cv2
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
from pathlib import Path


def draw_landmarks_on_image(rgb_image, detection_result):
  face_landmarks_list = detection_result.face_landmarks
  annotated_image = np.copy(rgb_image)

  # Loop through the detected faces to visualize.
  for idx in range(len(face_landmarks_list)):
    face_landmarks = face_landmarks_list[idx]

    # Draw the face landmarks.
    face_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
    face_landmarks_proto.landmark.extend([
      landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in face_landmarks
    ])

    solutions.drawing_utils.draw_landmarks(
        image=annotated_image,
        landmark_list=face_landmarks_proto,
        connections=mp.solutions.face_mesh.FACEMESH_TESSELATION,
        landmark_drawing_spec=None,
        connection_drawing_spec=mp.solutions.drawing_styles
        .get_default_face_mesh_tesselation_style())
    solutions.drawing_utils.draw_landmarks(
        image=annotated_image,
        landmark_list=face_landmarks_proto,
        connections=mp.solutions.face_mesh.FACEMESH_CONTOURS,
        landmark_drawing_spec=None,
        connection_drawing_spec=mp.solutions.drawing_styles
        .get_default_face_mesh_contours_style())
    solutions.drawing_utils.draw_landmarks(
        image=annotated_image,
        landmark_list=face_landmarks_proto,
        connections=mp.solutions.face_mesh.FACEMESH_IRISES,
          landmark_drawing_spec=None,
          connection_drawing_spec=mp.solutions.drawing_styles
          .get_default_face_mesh_iris_connections_style())

  return annotated_image


import mediapipe as mp
from scipy.spatial.transform.rotation import Rotation as R
from dataclasses import dataclass

@dataclass(frozen=True)
class HeadScanResults:
    processed_image: np.ndarray
    head2cam_transform_mat: np.ndarray
    head_visible: bool


class HeadScanner:
    def __init__(self, visualize=False):        
        self.visualize = visualize

        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        from mediapipe.tasks.python.vision.core import vision_task_running_mode
        run_video_mode = vision_task_running_mode.VisionTaskRunningMode.VIDEO
        # STEP 2: Create an FaceLandmarker object.
        base_options = python.BaseOptions(model_asset_path=str(Path(__file__).parent / 'face_landmarker.task'))
        options = vision.FaceLandmarkerOptions(base_options=base_options,
                                            output_face_blendshapes=False,
                                            output_facial_transformation_matrixes=True,
                                            num_faces=1, running_mode=run_video_mode)
        self.detector =  vision.FaceLandmarker.create_from_options(options)

        self.camera_matrix =np.array([[1080.1,   0., 950.2],
                                [  0.,1080.15, 475.0],
                                [  0.,     0., 1.   ]])
        self.mdists = np.zeros((1, 4), dtype=float)

        self.landmarks_head_space = None
        self.head2cam_transform_mat = None

        self.pcf = PCF(1920, 1080, self.camera_matrix[1,1])
        self.raw_landmarks = None
        self.raw_transform = None
    
    def draw_detected_landmarks(self, image):
        if self.visualize:
            image[:] = draw_landmarks_on_image(image, self.detection_result)

    def process(self, frame, timestamp): # image should be undistorted
        # frame = frame
        # STEP 3: Load the input image.
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(mp.ImageFormat.SRGB, frame_rgb)

        # STEP 4: Detect face landmarks from the input image.
        self.detection_result = self.detector.detect_for_video(image, timestamp)

        if self.detection_result.face_landmarks:
            self.raw_landmarks = self.detection_result.face_landmarks[0]
            landmarks = np.array([(lm.x,lm.y,lm.z) for lm in self.raw_landmarks])
            # print(self.detection_result.facial_transformation_matrixes)
            landmarks = landmarks.T


            # landmarks_head_space, _, head2cam_transform_mat = get_metric_landmarks_of_refined(landmarks.copy(), self.pcf)
            head2cam_transform_mat = self.detection_result.facial_transformation_matrixes[0]
            # landmarks_head_space = landmarks_head_space.T / 100

            head2cam_transform_mat = head2cam_transform_mat.T
            head2cam_transform_mat[3, :3] /= 100
            self.raw_transform = head2cam_transform_mat.copy()

            tr1 = Transform()
            tr1.set_matrix(head2cam_transform_mat)
            tr1.rotate(tr1.get_up(), 180)
            head2cam_transform_mat = tr1.get_matrix()

            rot = R.from_rotvec(Transform.WORLD_UP * np.pi)
            # landmarks_head_space = rot.apply(landmarks_head_space)

            if self.head2cam_transform_mat is not None:
                self.head2cam_transform_mat = self.head2cam_transform_mat * 0.2 + head2cam_transform_mat * 0.8
                # self.landmarks_head_space = self.landmarks_head_space * 0.2 + landmarks_head_space * 0.8
            else:
                self.head2cam_transform_mat = head2cam_transform_mat
                # self.landmarks_head_space = landmarks_head_space
            if self.visualize:
                self.draw_detected_landmarks(frame)
        else:
            self.raw_landmarks = None
            self.landmarks_head_space = None
            self.head2cam_transform_mat = None
            self.raw_transform = None
        
        res = HeadScanResults(frame, self.head2cam_transform_mat, self.is_head_visible())
        return res

    def is_head_visible(self):
        return self.raw_landmarks is not None
from obj_models.lab_stend import LabStend
import numpy as np
import cv2


class CommandsDrawer:
    def __init__(self, lab_stend: LabStend, ppi=50, marker_r_cm=2,
                target_color=(240, 50, 0), 
                cursor_color=(0, 100, 250)) -> None:
        
        self.lab_stend = lab_stend
        self._ppi = ppi
        self.__image = None
        self.marker_r_cm = marker_r_cm
        self.target_color = target_color
        self.cursor_color = cursor_color
        self.__target_relative = None
        self.__intersection = None

    def _init_image(self):
        width_pix, height_pix = self._image_size
        ratio = width_pix / height_pix
        if self.__image is None:
            self.__image = np.full((height_pix, width_pix, 3), 255, np.uint8)
        elif self.__image.shape[:2] == (height_pix, width_pix):
            self.__image[:] = 255
        else:
            self.__image = np.full((height_pix, width_pix, 3), 255, np.uint8)

    @property
    def ppi(self):
        return self._ppi
    
    @ppi.setter
    def ppi(self, ppi):
        ppi = float(ppi)
        if ppi <= 0:
            raise ValueError(f'ppi should be non-negative, found = {ppi}')
        self._ppi = ppi

    @property
    def image(self):
        return self.__image

    @property
    def marker_r_pix(self):
        return 50
        return int(np.ceil(self.marker_r_cm / 2.54 * self.ppi))

    @property
    def _image_size(self):
        vertices = self.lab_stend.screen_vertices
        hor_inch = np.linalg.norm(vertices['lu'] - vertices['ru']) * 100 / 2.54
        vert_inch = np.linalg.norm(vertices['ru'] - vertices['rb']) * 100 / 2.54
        width_pix, height_pix = hor_inch * self.ppi, vert_inch * self.ppi

        return np.ceil(width_pix).astype(int), np.ceil(height_pix).astype(int)
    
    @property
    def target(self):
        if self.target_specified:
            vertices = self.lab_stend.screen_vertices
            x, y = self.target_relative
            hor = vertices['ru'] - vertices['lu']
            vert =  vertices['lb'] - vertices['lu']
            point = vertices['lu'] + x * hor + y * vert
            return point
        return None

    @property
    def target_relative(self):
        return self.__target_relative
    
    @property
    def target_px(self):
        if self.target_specified:
            x, y = self.__target_relative
            width_pix, height_pix = self._image_size
            px, py = x * width_pix, y * height_pix
            return int(px), int(py)
        
    @property
    def target_specified(self):
        return self.__target_relative is not None
    
    @property
    def intersection(self):
        return self.__intersection
    
    @property
    def intersection_relative(self):
        if self.intersection_specified:
            vertices = self.lab_stend.screen_vertices

            lu = vertices['lu']
            ru = vertices['ru']
            lb = vertices['lb']

            hit_vec = self.intersection - lu
            hor_vec = ru - lu
            vert_vec = lb - lu
            x = hor_vec @ hit_vec / np.dot(hor_vec, hor_vec)
            y = vert_vec @ hit_vec / np.dot(vert_vec, vert_vec)
            return x, y
    
    @property
    def intersection_px(self):
        if self.intersection_specified:
            x, y = self.intersection_relative
            width_pix, height_pix = self._image_size
            px, py = x * width_pix, y * height_pix
            return int(px), int(py)

    @property
    def intersection_specified(self):
        return self.__intersection is not None

    def update_target_relative(self, target_relative):
        self.__target_relative = target_relative
    
    def update_intersection(self, intersection):
        self.__intersection = intersection

    def update_view(self):
        self._init_image()

        if self.target_specified:
            px, py = self.target_px
            cv2.circle(self.__image, (px, py), self.marker_r_pix, self.target_color, -1, cv2.LINE_AA)

        if self.intersection_specified:
            px, py = self.intersection_px
            cv2.circle(self.__image, (px, py), int(self.marker_r_pix*0.9), self.cursor_color, -1, cv2.LINE_AA)
            cv2.circle(self.__image, (px, py), int(self.marker_r_pix*0.1), (255, 255, 255), -1, cv2.LINE_AA)

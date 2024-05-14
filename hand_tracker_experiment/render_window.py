import cv2, numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer, QSize
from experiments_common.draw_experiment_grid_layout import draw_experiment_layout, draw_intersection_marker, draw_target_marker
from experiments_common.grid_commands_generator import GridCommandsGenerator

from forms.label_image import LabelImage


class CommandsTracker:
    def __init__(self) -> None:
        self.__target_rel = None
        self.__intersection_pix = None

        self.__base_image = None
        self.__processed_image = None
        self._marker_r_pix = 50

    def update_base_image(self, image):
        self.__base_image = image
        self.__processed_image = self.__base_image

    @property
    def image(self):
        return self.__processed_image

    @property
    def target_specified(self):
        return self.__target_rel is not None

    @property
    def intersection_specified(self):
        return self.__intersection_pix is not None

    def update_target_rel(self, target):
        self.__target_rel = target
    
    def update_intersection_pix(self, intersection):
        self.__intersection_pix = intersection

    def update_image(self, commands_generator: GridCommandsGenerator):
        if self.__base_image is not None:
            img = self.__base_image.copy()

            draw_experiment_layout(img, self._marker_r_pix, commands_generator)

            if self.target_specified:
                x, y = self.__target_rel
                target_pix = int(x*img.shape[1]), int(y*img.shape[0])
                draw_target_marker(img, target_pix, self._marker_r_pix)

            if self.intersection_specified:
                draw_intersection_marker(img, self.__intersection_pix, self._marker_r_pix)
            self.__processed_image = img



class RenderWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.commands_tracker = CommandsTracker()
        self.setup_ui()

        self.show_intersection = True

        self._update_timer = QTimer(self)
        self._update_timer.setInterval(int(1000/20))
        self._update_timer.timeout.connect(self.update_view)
        self._update_timer.start()
        self.commands_generator = GridCommandsGenerator(0, 0, 0)

    def setup_ui(self):
        self.render_preview = LabelImage()
        vbox = QVBoxLayout()
        vbox.addWidget(self.render_preview)
        self.setLayout(vbox)

    def set_intersection_pix(self, intersection):
        self.intersection_pix = intersection

        if self.show_intersection:
            self.commands_tracker.update_intersection_pix(self.intersection_pix)
        else:
            self.commands_tracker.update_intersection_pix(None)

    def set_target_rel(self, target):
        self.commands_tracker.update_target_rel(target)

    def set_base_cvimage(self, image):
        self.commands_tracker.update_base_image(image)

    def set_pixmap_preview(self, pixmap):
        self.render_preview.setPixmap(pixmap)

    def set_commands_generator(self, commands_generator: GridCommandsGenerator):
        self.commands_generator = commands_generator

    def update_view(self):
        self.commands_tracker.update_image(self.commands_generator)
        img = self.commands_tracker.image
        if img is not None:
            self.render_preview.setCVImage(img)

    
from typing import List
from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QGridLayout, QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsTextItem
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QResizeEvent, QColor, QImage, QPixmap, QColorConstants, QPen, QBrush
from PyQt6.QtCore import Qt, QSize, QPointF, QObject, pyqtSignal
import numpy as np
from enum import Enum
from experiments_common.grid_commands_generator import GridCommand, GridCommandsGenerator


class MarkerRole(Enum):
    CURSOR_REAL = 0
    TARGET_ACTIVE = 1
    TARGET_NOT_ACTIVE = 2
    TARGET_BEST_MATCH = 3
    TARGET_ACTIVE_AND_BEST_MATCH = 4


class GridExperimentPalette:
    def __init__(self, cursor_color = QColor(255, 167, 43, 220),
                 active_target_color = QColor(230, 20, 20, 255),
                 not_active_target_color = QColor(120, 120, 120, 180),
                 target_best_match_color= QColor(242, 219, 85, 180),
                 target_active_and_best_match_color = QColor(101, 235, 110, 255),
                 grid_line_color: QColor = QColor(80, 80, 80, 180)):
        self._cursor_color = cursor_color
        self._active_target_color = active_target_color
        self._not_active_target_color = not_active_target_color
        self._target_best_match_color = target_best_match_color
        self._target_active_and_best_match_color = target_active_and_best_match_color
        self._grid_line_color = grid_line_color
    
    def cursor_color(self):
        return QColor(self._cursor_color)
    
    def active_target_color(self):
        return QColor(self._active_target_color)

    def not_active_target_color(self):
        return QColor(self._not_active_target_color)
    
    def target_best_match_color(self):
        return QColor(self._target_best_match_color)
    
    def target_active_and_best_match_color(self):
        return self._target_active_and_best_match_color

    # def set_cursor_color()


class Marker:
    def __init__(self, code, radius,# gr_text_ref: QGraphicsTextItem,
                 position: QPointF,
                 grid_experiment_palette: GridExperimentPalette, 
                 role: MarkerRole=MarkerRole.TARGET_NOT_ACTIVE) -> None:
        self._code = code
        self._radius = radius
        self._position = position
        self._role = role
        self._gr_item: QGraphicsEllipseItem = QGraphicsEllipseItem(0, 0, 10, 10)
        self.set_palette(grid_experiment_palette)
        self.set_role(role)
        self._update_gr_item()

    def graphics_item(self):
        return self._gr_item

    def position(self):
        premitive_pos = self._gr_item.pos()
        marker_pos = QPointF(premitive_pos.x() + self._radius, premitive_pos.y() + self._radius)
        return marker_pos
    
    def set_position(self, pos: QPointF|None):
        self._position = pos
        self._update_gr_item()

    def set_radius(self, r: float):
        self._radius = r
        self._update_gr_item()

    def _update_gr_item(self):
        r = self._radius
        pos = self._position
        if pos is None:
            if self._gr_item.isVisible():
                self._gr_item.setVisible(False)
        else:
            if not self._gr_item.isVisible():
                self._gr_item.setVisible(True)
            self._gr_item.setRect(pos.x() - r, pos.y() - r, r*2, r*2)

    def code(self):
        return self._code

    def set_palette(self, palette: GridExperimentPalette):
        self._grid_experiment_palette = palette
        self._update_marker_view()

    def set_role(self, role: MarkerRole):
        if role != self._role:
            self._role = role
            self._update_marker_view()

    def _update_marker_view(self):
        match self._role:
            case MarkerRole.CURSOR_REAL:
                self._gr_item.setBrush(self._grid_experiment_palette.cursor_color())
                self._gr_item.setZValue(1)
            case MarkerRole.TARGET_ACTIVE:
                self._gr_item.setBrush(self._grid_experiment_palette.active_target_color())
                self._gr_item.setZValue(0.5)
            case MarkerRole.TARGET_NOT_ACTIVE:
                self._gr_item.setBrush(self._grid_experiment_palette.not_active_target_color())
                self._gr_item.setZValue(0.5)
            case MarkerRole.TARGET_BEST_MATCH:
                self._gr_item.setBrush(self._grid_experiment_palette.target_best_match_color())
                self._gr_item.setZValue(0.5)
            case MarkerRole.TARGET_ACTIVE_AND_BEST_MATCH:
                self._gr_item.setBrush(self._grid_experiment_palette.target_active_and_best_match_color())
                self._gr_item.setZValue(0.5)
    
    def role(self):
        return self._role

    def set_visible(self, value: bool):
        self._gr_item.setVisible(value)
    
    def is_visible(self):
        return self._gr_item.isVisible()


class GridExperimentDrawer(QWidget):
    drawing_surface_size_changed = pyqtSignal(QSize)
    def __init__(self,
                 default_drawing_surface_size: QSize = QSize(300, 300),
                 marker_r = 60,
                 grid_experiment_palette: GridExperimentPalette = None,
                 parent=None) -> None:
        super().__init__(parent=parent)

        
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)

        grid = QGridLayout()
        grid.addWidget(self.view)
        self.setLayout(grid)

        self._marker_r = marker_r
        self._cursor_center:  QPointF = None
        self._active_target_center: QPointF = None
        self._not_active_target_centers: List[QPointF] = None
        self._row_separators: List[int] = None
        self._column_separators: List[int] = None

        self._grid_experiment_palette = grid_experiment_palette

        self._base_image_gr_item: QGraphicsPixmapItem = QGraphicsPixmapItem(QPixmap())
        self._base_image_gr_item.setZValue(-1)

        self._r_sep_gr_items: List[QGraphicsLineItem] = []
        self._c_sep_gr_items: List[QGraphicsLineItem] = []
        self._markers: List[Marker] = []
        self._line_width = 20 

        self.scene.addItem(self._base_image_gr_item)
        
        self.set_experiment_palette(self._grid_experiment_palette)

        self.set_default_drawing_surface_size(default_drawing_surface_size)
    # colors and brushes

    def set_experiment_palette(self, grid_experiment_palette: GridExperimentPalette):
        self._grid_experiment_palette = grid_experiment_palette or GridExperimentPalette()

    def experiment_palette(self):
        return self._grid_experiment_palette

    def grid_line_pen(self):
        return QPen(self._grid_experiment_palette._grid_line_color, self._line_width)
    
    # base image configuration
    
    def set_base_image(self, image: QImage|None):
        size_at_start = self.drawing_surface_size()
        if image is not None:
            self._base_image_gr_item.setPixmap(QPixmap.fromImage(image))
        else:
            self._base_image_gr_item.setPixmap(QPixmap(self.default_drawing_surface_size()))
        self.tighten_scene_to_view()
        size_at_end = self.drawing_surface_size()
        
        if size_at_start != size_at_end:
            self._update_markers_radius()
            self._update_line_width()
            self.drawing_surface_size_changed.emit(size_at_end)
    
    def set_default_drawing_surface_size(self, size: QSize):
        size_at_start = self.drawing_surface_size()
        self._default_drawing_surface_size = size
        self._base_image_gr_item.setPixmap(QPixmap(self._default_drawing_surface_size))
        # self.set_base_image(None)
        self.tighten_scene_to_view()
        size_at_end = self.drawing_surface_size()
        if size_at_start != size_at_end:
            self._update_markers_radius()
            self._update_line_width()
            self.drawing_surface_size_changed.emit(size_at_end)

    def _update_markers_radius(self):
        size = self.drawing_surface_size()
        min_dim = min(size.width(), size.height())
        marker_size = min_dim / 18
        self._marker_r = marker_size
        for marker in self._markers:
            marker.set_radius(marker_size)

    def _update_line_width(self):
        size = self.drawing_surface_size()
        min_dim = min(size.width(), size.height())
        self._line_width = min_dim / 54
        pen = self.grid_line_pen()
        for line in [*self._r_sep_gr_items, *self._c_sep_gr_items]:
            line.setPen(pen)

    def tighten_scene_to_view(self):
        size = self.drawing_surface_size()
        self.view.setSceneRect(0, 0, size.width(), size.height())
        self.view.fitInView(self._base_image_gr_item, Qt.AspectRatioMode.KeepAspectRatio)

    def default_drawing_surface_size(self):
        return self._default_drawing_surface_size

    def drawing_surface_size(self):
        if self._base_image_gr_item is not None:# and not self._base_image_gr_item.pixmap().isNull():
            return self._base_image_gr_item.pixmap().size()
        else:
            return self._default_drawing_surface_size

    # visible elements of drawer

    def markers(self):
        return self._markers.copy()

    def create_marker(self, code, center: QPointF, role: MarkerRole):
        marker = Marker(code, self._marker_r, center, self.experiment_palette(), role)
        self._markers.append(marker)
        self.scene.addItem(marker.graphics_item())
        return marker
    
    def remove_marker(self, marker: Marker):
        if marker in self._markers:
            self._markers.remove(marker)
        self.scene.removeItem(marker._gr_item)

    def row_separators(self) -> List[float]:
        return self._row_separators
    
    def set_row_separators(self, r_sep:List[int]|None):
        if r_sep is not None:
            r_sep = np.asarray(r_sep, dtype=int).tolist()
            self._row_separators = r_sep
        else:
            self._row_separators = []
        
        for line in self._r_sep_gr_items:
            self.scene.removeItem(line)

        self._r_sep_gr_items.clear()

        size = self.drawing_surface_size()
        w, h = size.width(), size.height()
        pen = self.grid_line_pen()
        for line_y in self._row_separators:
            line = QGraphicsLineItem(0, line_y, w, line_y)
            line.setPen(pen)
            line.setZValue(-0.5)
            self.scene.addItem(line)
            self._r_sep_gr_items.append(line)

    def column_separators(self) -> List[float]:
        return self._column_separators
    
    def set_column_separators(self, c_sep:List[int]|None):
        if c_sep is not None:
            c_sep = np.asarray(c_sep, dtype=int).tolist()
            self._column_separators = c_sep
        else:
            self._column_separators = []

        for line in self._c_sep_gr_items:
            self.scene.removeItem(line)
        
        self._c_sep_gr_items.clear()

        size = self.drawing_surface_size()
        w, h = size.width(), size.height()
        pen = self.grid_line_pen()
        for line_x in self._column_separators:
            line = QGraphicsLineItem(line_x, 0, line_x, h)
            line.setPen(pen)
            line.setZValue(-0.5)
            self.scene.addItem(line)
            self._c_sep_gr_items.append(line)

    def resizeEvent(self, a0: QResizeEvent) -> None:
        self.view.fitInView(self._base_image_gr_item, Qt.AspectRatioMode.KeepAspectRatio)
        return super().resizeEvent(a0)
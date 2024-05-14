from typing import List
from experiments_common.grid_commands_generator import GridCommand, GridCommandsGenerator
from experiments_common.grid_experiment_drawer import GridExperimentDrawer, Marker, MarkerRole
from PyQt6.QtCore import QPointF, QObject, QSize, pyqtSlot
from PyQt6.QtGui import QImage
import numpy as np


class GridCommandsController(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._commands_generator: GridCommandsGenerator = GridCommandsGenerator(0)
        self._grid_drawer: GridExperimentDrawer = None
        self._centers_markers: List[Marker] = []
        self._cursor_marker: Marker = None
        self._do_show_best_match_command = True
        self._drawer_size_changed_connection = None

    def is_show_best_match_command(self):
        return self._do_show_best_match_command

    def set_show_best_match_command(self, value: bool):
        self._do_show_best_match_command = bool(value)
        if not self._do_show_best_match_command:
            for marker in self._centers_markers:
                if marker.role() == MarkerRole.TARGET_BEST_MATCH:
                    marker.set_role(MarkerRole.TARGET_NOT_ACTIVE)
    
    def set_show_cursor(self, value: bool):
        self._do_show_cursor = bool(value)
        self._cursor_marker.set_visible(self._do_show_cursor)
        print('self._cursor_marker.is_visible()', self._cursor_marker.is_visible())

    def grid_commands_generator(self):
        return self._commands_generator

    def set_grid_commands_generator(self, grid_commands_generator: GridCommandsGenerator):
        assert grid_commands_generator is not None
        self._commands_generator = grid_commands_generator
        self._configure_drawer()
    
    def set_drawer(self, grid_drawer: GridExperimentDrawer):
        if self._grid_drawer != None:
            del self._drawer_size_changed_connection
        self._grid_drawer = grid_drawer
        self._drawer_size_changed_connection = self._grid_drawer.drawing_surface_size_changed.connect(self._drawer_size_changed)
        self._configure_drawer()

    @pyqtSlot(QSize)
    def _drawer_size_changed(self, size):
        self._configure_drawer()

    def _clear_markers(self):
        if self._grid_drawer is not None:
            for marker in self._centers_markers:
                self._grid_drawer.remove_marker(marker)
            if self._cursor_marker is not None:
                self._grid_drawer.remove_marker(self._cursor_marker)
            self._centers_markers.clear()
            self._cursor_marker = None

    def _configure_drawer(self):
        if self._grid_drawer is None:
            return
        self._clear_markers()
        centers_commands = self._commands_generator.grid_commands()
        size = self._grid_drawer.drawing_surface_size()
        # print(size)
        centers = [self._grid_drawer.create_marker(center.code,\
                                                   QPointF(center.x_rel*size.width(), center.y_rel*size.height()),\
                                                   MarkerRole.TARGET_NOT_ACTIVE
                                                   ) for center in centers_commands]
        self._centers_markers.extend(centers)
        self._cursor_marker = self._grid_drawer.create_marker(-1, QPointF(0,0), MarkerRole.CURSOR_REAL)
        # self._cursor_marker.set_visible(False)

        self._grid_drawer.set_row_separators(self._commands_generator.row_separators()*size.height())
        self._grid_drawer.set_column_separators(self._commands_generator.column_separators()*size.width())
        self._set_target_command(self._commands_generator.current_target()[1])
        
        # self._target_changed_connection = self.grid_commands_generator().target_command_changed.connect(self._set_target_command)

    def _set_target_command(self, command: GridCommand|None):
        if command is None:
            for marker in self._centers_markers:
                if marker.role == MarkerRole.TARGET_ACTIVE:
                    marker.set_role(MarkerRole.TARGET_NOT_ACTIVE)
        else:
            for marker in self._centers_markers:
                if marker.code() == command.code:
                    marker.set_role(MarkerRole.TARGET_ACTIVE)
                elif marker.role() != MarkerRole.TARGET_BEST_MATCH:
                    marker.set_role(MarkerRole.TARGET_NOT_ACTIVE)

    def update_target_command_ind(self, command_ind: int|None):
        self._commands_generator.update_command_ind(command_ind)
        self._set_target_command(self._commands_generator.current_target()[1])

    def set_cursor_center(self, center: QPointF):
        self._cursor_marker.set_position(center)
        if center is not None:
            self._show_best_match_command(center)
        else:
            self._remove_best_match_command()

    def _show_best_match_command(self, cursor_center: QPointF|None):
        if not self._do_show_best_match_command:
            return
        if cursor_center is None:
            return
        best_command = self.best_match_command(cursor_center)
        for marker in self._centers_markers:
            if marker.code() != best_command.code:
                if marker.role() == MarkerRole.TARGET_BEST_MATCH:
                    marker.set_role(MarkerRole.TARGET_NOT_ACTIVE)
                elif marker.role() == MarkerRole.TARGET_ACTIVE_AND_BEST_MATCH:
                    marker.set_role(MarkerRole.TARGET_ACTIVE)
        for marker in self._centers_markers:
            if marker.code() == best_command.code:
                if marker.role() in (MarkerRole.TARGET_ACTIVE, MarkerRole.TARGET_ACTIVE_AND_BEST_MATCH):
                    marker.set_role(MarkerRole.TARGET_ACTIVE_AND_BEST_MATCH)
                else:
                    marker.set_role(MarkerRole.TARGET_BEST_MATCH)
                

    def _remove_best_match_command(self):
        for marker in self._centers_markers:
            if marker.role() == MarkerRole.TARGET_BEST_MATCH:
                marker.set_role(MarkerRole.TARGET_NOT_ACTIVE)
            elif marker.role() == MarkerRole.TARGET_ACTIVE_AND_BEST_MATCH:
                marker.set_role(MarkerRole.TARGET_ACTIVE)

    def best_match_command(self, cursor_center: QPointF):
        # centers_rel = self._commands_generator.centers()
        size = self._grid_drawer.drawing_surface_size()
        w, h = size.width(), size.height()
        # centers_pix = np.array([[center[0]*w, center[1]*h] for center in centers_rel], dtype=float)
        commands = self._commands_generator.grid_commands()
        centers_p = [self.get_command_position(com) for com in commands]
        centers_pix = np.array(list(map(lambda p: (p.x(), p.y()), centers_p)))
        distances = np.linalg.norm(centers_pix - [cursor_center.x(), cursor_center.y()], axis=1)
        # print(np.argmin(distances))
        best_command:GridCommand = commands[np.argmin(distances)]
        return best_command

    def get_command_position(self, command: GridCommand):
        size = self._grid_drawer.drawing_surface_size()
        if command is not None:
            return QPointF(command.x_rel*size.width(), command.y_rel*size.height())
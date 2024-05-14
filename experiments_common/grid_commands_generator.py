import numpy as np
from dataclasses import dataclass
from PyQt6.QtCore import QSize, QObject, pyqtSignal


@dataclass(frozen=True)
class GridCommand:
    code: int
    x_rel: float
    y_rel: float


class GridCommandsGenerator:
    pass


# class GridCommandsGeneratorIterator:
#     def __init__(self, commands_generator: GridCommandsGenerator) -> None:
#         self._commands_generator = commands_generator
#         self._ind = 0
#         self._commands_iter = iter(self._commands_generator.)
#     def __next__(self):
#         i


class GridCommandsGenerator(QObject):
    def __init__(self, max_commands, offset_l=0, offset_r=0,
                                   offset_u=0, offset_b=0) -> None:
        super().__init__()
        self._command_ind, self._current_target = None, None

        self._max_commands = max_commands
        if max_commands % 9 == 0:
            n_repeats = int(max_commands // 9)
        else:
            n_repeats = int(max_commands // 9) + 1
        
        self._offset_l = offset_l
        self._offset_r = offset_r
        self._offset_u = offset_u
        self._offset_b = offset_b

        assert offset_l >= 0 and offset_r >= 0 and offset_u >= 0 and offset_b >= 0
        assert offset_l + offset_r < 1
        assert offset_u + offset_b < 1
        """
        5 3 7
        1 0 2
        6 4 8
        """

        codes_shuffled = self.generate_commands_sequence(max_commands)

        code2command = {com.code:com for com in self.grid_commands()}

        commands = [code2command[code] for code in codes_shuffled]

        self._commands = commands

        # if n_repeats == 0:
        #     self._commands = []
        #     self._command_indexes = []
        #     self._command_positions = []
        # else:
        #     inds = np.repeat(np.array([5, 3, 7, 1, 0, 2, 6, 4, 8]), n_repeats)
        #     np.random.shuffle(inds)
        #     inds_shuffled = inds[:n_commands]
        #     centers_shuffled = centers[inds_shuffled]
        #     self._commands = [GridCommand(ind, center[0], center[1]) for ind, center in zip(inds_shuffled, centers_shuffled)]
        #     self._command_indexes = inds_shuffled
        #     self._command_positions = centers_shuffled

    def max_commands(self):
        return self._max_commands

    def generate_commands_sequence(self, n_commands):
        if n_commands % 9 == 0:
            n_repeats = int(n_commands // 9)
        else:
            n_repeats = int(n_commands // 9) + 1
        
        if n_repeats == 0:
            inds_shuffled = []
        else:
            inds  = np.repeat(np.array(self.codes(), dtype=int), n_repeats)

            np.random.seed(42)


            np.random.shuffle(inds)
            inds_shuffled = inds[:n_commands]
        return inds_shuffled
    
    def _left_line(self):
        return self._offset_l
    
    def _right_line(self):
        return 1-self._offset_r

    def _up_line(self):
        return self._offset_u

    def _bottom_line(self):
        return 1 - self._offset_b
    
    def _horizontal_span(self):
        return self._right_line() - self._left_line()
    
    def _vertical_span(self):
        return self._bottom_line() - self._up_line()

    def centers(self):
        v_span = self._vertical_span()
        h_span = self._horizontal_span()
        start_x = self._left_line()
        start_y = self._up_line()
        centers = []
        for j in range(3):
            for i in range(3):
                centers.append((start_x + h_span * (1/6 + i/3), start_y + v_span * (1/6 + j / 3)))
        centers = np.array(centers, float)
        return centers
    
    def codes(self):
        """
        5 3 7
        1 0 2
        6 4 8
        """
        return np.array([5, 3, 7, 1, 0, 2, 6, 4, 8])
        return np.arange(9)
    
    def grid_commands(self):
        codes = self.codes()
        centers = self.centers()
        commands = [GridCommand(code, center[0], center[1]) for code, center in zip(codes, centers)]
        # print('grid commands', commands)
        return commands

    def row_separators(self):
        h_span = self._horizontal_span()
        start_x = self._left_line()

        return start_x + h_span * np.array([1/3, 2/3])
    
    def column_separators(self):
        v_span = self._vertical_span()
        start_y = self._up_line()

        return start_y + v_span * np.array([1/3, 2/3])
    
    # def target_window_size(self, size: QSize):
    #     assert isinstance(size, QSize)
    #     self._target_window_size = size

    def current_target(self):
        return self._command_ind, self._current_target
            
    def update_command_ind(self, command_ind:int|None):
        if command_ind is None:
            self._command_ind = None
            self._current_target = None
            return False
        
        command = self._commands[command_ind]
        self._current_target = command
        self._command_ind = command_ind
        return True


    # def reset(self):
    #     self.__iter_ind = 0
    #     return self
        # return iter(self._commands)

    
        
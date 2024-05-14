import cv2, numpy as np

from .grid_commands_generator import GridCommandsGenerator

def draw_experiment_layout(image: np.ndarray, marker_r, commands_generator: GridCommandsGenerator):
    w, h = image.shape[1], image.shape[0]

    centers = commands_generator.centers()
    vlines = commands_generator.row_separators()
    hlines = commands_generator.column_separators()

    for coord in vlines:
        cv2.line(image, (int(coord*w), 0), (int(coord*w), h), (200, 220, 200), 10)
    
    for coord in hlines:
        cv2.line(image, (0, int(coord*h)), (w, int(coord*h)), (200, 220, 200), 10)

    for center in centers:
        x = int(center[0] * w)
        y = int(center[1] * h)
        cv2.circle(image, (x, y), marker_r, (210, 210, 210), -1, cv2.LINE_AA)

def draw_marker(image: np.ndarray, pos, marker_r, color):
    px, py = pos
    cv2.circle(image, (int(px), int(py)), marker_r, color, -1, cv2.LINE_AA)

def draw_target_marker(image: np.ndarray, target, marker_r, color=(240, 50, 0)):
    draw_marker(image, target, marker_r, color)

def draw_intersection_marker(image: np.ndarray, intersection, marker_r, color=(0, 100, 250)):
    draw_marker(image, intersection, marker_r, color)
    draw_marker(image, intersection, int(marker_r*0.1)+1, (255, 255, 255))
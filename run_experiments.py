import typing
from PyQt6 import QtCore
from experiments_main_widget import ExperimentsMainWidget
from PyQt6.QtWidgets import QApplication, QWidget
import sys
from PyQt6.QtCore import QThread
import threading


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ExperimentsMainWidget()
    window.show()
    app.exec()
    print(threading.enumerate())
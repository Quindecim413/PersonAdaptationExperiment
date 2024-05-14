from dataclasses import dataclass
import typing
import serial
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThreadPool,QIODeviceBase
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo
from utils.threading import Worker


class GlassesReader(QObject):
    started = pyqtSignal()
    data_changed = pyqtSignal(np.ndarray)
    finished = pyqtSignal()
    error_occured = pyqtSignal(str)
    def __init__(self, port_info: QSerialPortInfo,
                 baudrate:QSerialPort.BaudRate=QSerialPort.BaudRate.Baud115200):
        super().__init__()
        self._port_info = port_info
        self._baudrate = baudrate
        self._serial_port: QSerialPort = None
        self._error_occured = False

    @pyqtSlot(QSerialPort.SerialPortError)
    def _recieved_error(self, err: QSerialPort.SerialPortError):
        if err == QSerialPort.SerialPortError.NoError:
            return
        self._error_occured = True
        self.error_occured.emit(self._serial_port.errorString())

    def port_info(self):
        return self._port_info

    def open(self):
        if self._serial_port is not None and self._serial_port.isOpen():
            self.close()
        
        self._serial_port = QSerialPort(self._port_info)
        self._serial_port.setBaudRate(115200)
        # self._serial_port.setBaudRate(QSerialPort.BaudRate.Baud115200)#self._baudrate.value)
        self._serial_port.errorOccurred.connect(self._recieved_error)
        self._serial_port.dataTerminalReadyChanged.connect(self._terminal_ready_changed)
        self._serial_port.setDataBits(QSerialPort.DataBits.Data8)
        self._serial_port.setParity(QSerialPort.Parity.NoParity)
        self._serial_port.setStopBits(QSerialPort.StopBits.OneStop)
        self._serial_port.setFlowControl(QSerialPort.FlowControl.NoFlowControl)
        import serial
        # with 
        # print(serial.Serial(self._port_info.portName(), 115200).readline().decode('utf-8'))
        self._serial_port.readyRead.connect(self._read_from_serial)
        
        self._serial_port.open(QIODeviceBase.OpenModeFlag.ReadOnly)
        self._serial_port.setDataTerminalReady(True)
        
    def is_running(self):
        return self._serial_port is not None and self._serial_port.isOpen()
    
    def is_correct(self):
        return not self._error_occured

    @pyqtSlot(bool)
    def _terminal_ready_changed(self, is_ready:bool):
        if is_ready:
            self.started.emit()
        else:
            self.finished.emit()

    def close(self):
        if self._serial_port is None:
            return
        if self._serial_port.isOpen():
            self._serial_port.close()

    def _read_from_serial(self):
        while self._serial_port.canReadLine():
            line = self._serial_port.readLine().data().decode()
            # print('line', line); print(line.decode())
            line = line.replace('\r', '').replace('\n', '')
            # print(line)
            elems = np.array(list(map(float, line.split())), dtype=float)
            self.data_changed.emit(elems)

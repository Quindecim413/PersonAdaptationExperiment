from dataclasses import dataclass
import typing
import serial
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThreadPool, QIODeviceBase
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo
from utils.threading import Worker
from serial import Serial 
from time import time
# from scipy.signal import butter, lfilter
# from scipy.signal import freqs

# def butter_lowpass(cutOff, fs, order=5):
#     nyq = 0.5 * fs
#     normalCutoff = cutOff / nyq
#     b, a = butter(order, normalCutoff, btype='low', analog = True)
#     return b, a

# def butter_lowpass_filter(data, cutOff, fs, order=4):
#     b, a = butter_lowpass(cutOff, fs, order=order)
#     y = lfilter(b, a, data)
#     return y

def low_pass_filter(adata: np.ndarray, bandlimit: int = 1000, sampling_rate: int = 44100) -> np.ndarray:
    # translate bandlimit from Hz to dataindex according to sampling rate and data size
    bandlimit_index = int(bandlimit * adata.size / sampling_rate)

    fsig = np.fft.fft(adata)
    
    for i in range(bandlimit_index + 1, len(fsig) - bandlimit_index ):
        fsig[i] = 0
        
    adata_filtered = np.fft.ifft(fsig)

    return np.real(adata_filtered)

from sklearn.linear_model import LinearRegression
from skforecast.ForecasterAutoreg import ForecasterAutoreg


class _GlassesReader(QObject):
    started = pyqtSignal()
    data_changed = pyqtSignal(np.ndarray)
    finished = pyqtSignal()
    error_occured = pyqtSignal(Exception, str)

    def __init__(self, port_name: str) -> None:
        super().__init__()
        self._port_name = port_name
        self._serial_port = None
        self._stopping = False

        self._runing_dt = 1/80
        self._last_ts = None
        self._values_buffer = []
        self._store_data_time = 0.1

        self._num_lags = 10
        # self._forecast_model = ForecasterAutoreg(LinearRegression(), lags=self._num_lags)

    
    def is_running(self) -> bool:
        if self._serial_port is None:
            return False
        return self._serial_port.is_open

    def start(self):
        try:
            self._serial_port = Serial(self._port_name, 115200, timeout=0.1, inter_byte_timeout=0.1)
            self.started.emit()
        except Exception as e:
            import traceback
            self.error_occured.emit(e, traceback.format_exc())
        

    def stop(self):
        self._stopping = True
        try:
            if self._serial_port is not None and self._serial_port.is_open:
                self._serial_port.close()
        except Exception as e:
            import traceback
            self.error_occured.emit(e, traceback.format_exc())
        finally:
            self.finished.emit()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args, **kw_args):
        self.stop()

    def start_read_data(self):
        if self._serial_port is None or not self._serial_port.is_open:
            raise ValueError('Serial should be opened first')
        try:
            while self._serial_port.is_open:
                # print('a', end='\t')
                line = self._serial_port.read_until().decode()
                # print(line)
                if line.count('\t') != 3:
                    continue
                line = line.replace('\r', '').replace('\n', '')
                elems = np.array(list(map(float, line.split())), dtype=float)

                ts = time()
                if self._last_ts is None:
                    self._last_ts = ts
                    dt = self._runing_dt
                else:
                    dt = ts - self._last_ts
                
                self._runing_dt = 0.8 * self._runing_dt + 0.2 * dt
                self._last_ts = ts
                

                self._values_buffer.append(elems)
                store_elems = int(np.ceil(self._store_data_time * (1 / self._runing_dt)))
                if len(self._values_buffer) > store_elems:
                    self._values_buffer = self._values_buffer[-store_elems:]

                # print('self._runing_dt', round(self._runing_dt, 3), ', len_buffer', len(self._values_buffer))


                vals_arr = np.asarray(self._values_buffer, float)
                # print(vals_arr)
                filtered_values = np.array([low_pass_filter(vals_arr[:, col_ind], 5, 1/self._runing_dt) for col_ind in range(vals_arr.shape[1])]).T
                # filtered_values = low_pass_filter(self._values_buffer, 10, 1/self._runing_dt)

                # self._values_buffer.append(elems)

                # store_elems = self._store_data_time * self._runing_dt
                # if len(self._values_buffer) > self._store_data_time * self._runing_dt:
                #     store_elems
                # self._values_buffer = self._values_buffer[-self._num_lags:]
                # if len(self._values_buffer) == self._num_lags:
                #     reg = LinearRegression.fit()

                final_elems = filtered_values[-1]
                # print(final_elems)
                self.data_changed.emit(final_elems)
                # self.data_changed.emit(elems)
        except Exception as e:
            if self._stopping:
                return
            import traceback
            self.error_occured.emit(e, traceback.format_exc())

    # def start_read_data(self):
    #     if self._serial_port is None or not self._serial_port.is_open:
    #         raise ValueError('Serial should be opened first')
    #     try:
    #         buff = ''
    #         while self._serial_port.is_open:
    #             # print('a', end='\t')
    #             if self._serial_port.in_waiting > 0:
    #                 scanned = self._serial_port.read(self._serial_port.in_waiting).decode()
    #                 buff += scanned

    #                 print(scanned)

    #                 buff = buff.lstrip()
    #                 while '\n' in buff:
    #                     line_end_index = buff.index('\n')
    #                     # print(line_end_index)
    #                     line = buff[:line_end_index]
    #                     buff = buff[line_end_index:]
    #                     line = line.replace('\r', '').replace('\n', '')
    #                     elems = np.array(list(map(float, line.split())), dtype=float)
    #                 #     # self.data_changed.emit(elems)
    #                     # self.data_changed.emit(elems)
    #             time.sleep(0.01)
    #     except Exception as e:
    #         import traceback
    #         self.error_occured.emit(e, traceback.format_exc())
    


class GlassesReader(QObject):
    started = pyqtSignal()
    data_changed = pyqtSignal(np.ndarray)
    finished = pyqtSignal()
    error_occured = pyqtSignal(str)
    def __init__(self, port_info: QSerialPortInfo):
        super().__init__()
        self._port_info = port_info
        self._threadpool = QThreadPool()
        self._worker = None
        self._reader = None
        self._error_occured = False

    def _recieved_error(self, ex: Exception, text):
        self._error_occured = True
        # import traceback
        # print(traceback.format_exc())
        self.error_occured.emit(text)

    def port_info(self):
        return self._port_info

    def _process_reader_in_thread(self, reader: _GlassesReader):
        with reader:
            reader.start()
            reader.start_read_data()

    def open(self):
        if self.is_running():
            return
        self._reader = _GlassesReader(self._port_info.portName())
        self._reader.started.connect(self.started.emit)
        self._reader.data_changed.connect(lambda data: (self.data_changed.emit(data)))#, print(data)))
        self._reader.finished.connect(self.finished.emit)
        self._reader.error_occured.connect(self._recieved_error)

        self._worker = Worker(self._process_reader_in_thread, self._reader)

        def remove_reader():
            self._reader = None
        self._worker.signals.finished.connect(remove_reader)

        self._threadpool.start(self._worker)
        
    def is_running(self):
        return self._reader is not None and self._reader.is_running()
    
    def is_correct(self):
        return not self._error_occured

    def close(self):
        if self._reader is None:
            return
        del self._worker
        # print()
        if self._reader.is_running():
            self._reader.stop()
            self._threadpool.waitForDone()
import serial, h5py, numpy as np

buff = []
ser = serial.Serial('COM4', baudrate=115200)

while len(buff) < 2000:
    print(len(buff))
    line = ser.readline().decode().replace('\r', '').replace('\n', '')
    # print(line,line.split('\t'))
    vals = list(map(float, line.split('\t')[:3]))
    buff.append(vals)

with h5py.File('sample_record.hdf5', 'w') as f:
    f.create_dataset('data', data=np.array(buff))

ser.close()

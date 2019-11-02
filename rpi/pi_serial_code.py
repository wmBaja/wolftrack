import serial
from time import sleep

ser = serial.Serial('/dev/ttyACM0', 9600)

def getSensors(sen):
    alength = len(sen)
    a = []
    for x in range(0, alength, 2):
        if x == 0:
            b = sen[0:2]
            a.append(getValue(b))
        else:
            b = sen[x*2:x*2+2]
            a.append(getValue(b))
    return a

def getValue(arr):
    return int.from_bytes(arr, byteorder='big', signed=False)

while True:
    t = list((ser.read(2)))
    a = getSensors(t)
    sleep(1)
    val = getValue(t)
    for x in a:
        print(x, end=' ')
    print ()
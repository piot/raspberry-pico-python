import machine

from machine import Pin, I2C

import sh1106

def scan():
    devices = i2c.scan()

    if len(devices) != 0:
        print('Number of I2C devices found=',len(devices))
        for device in devices:
            print("Device Hexadecimal Address= ",hex(device))
    else:
        print("No device found")

sdaPIN = Pin(2)
sclPIN = Pin(3)
i2c = I2C(1,sda=sdaPIN, scl=sclPIN, freq=400000)

scan()

display = sh1106.SH1106_I2C(128,64,i2c)
display.sleep(False)
for x in range(600):
    display.fill(0)
    display.text('Hello world!', 128 - x, 32, 1)
    for n in range(10):
        display.pixel(x + n*4, n * 10, 1)
    display.show()

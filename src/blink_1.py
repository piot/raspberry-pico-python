from machine import I2C, Pin
from I2C_LCD import I2CLcd
import time

i2c_port1 = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)

lcd_address = 39
lcd = I2CLcd(i2c_port1, lcd_address, 2, 16)
lcd.move_to(0, 0)
lcd.putstr("Hello")
        
lcd.move_to(0, 1)
lcd.putstr("World!")

led_on_pico = Pin(25, Pin.OUT)
red_led = Pin(15, Pin.OUT)
button = Pin(13, Pin.IN, Pin.PULL_UP)
flash_timer = 0
button_press_count = 0

while True:
    led_on_pico.value(1)
    time.sleep(0.1)
    led_on_pico.value(0)
    time.sleep(0.1)
    
    button_down = not button.value()
    if button_down and flash_timer == 0:
       flash_timer = 10
       lcd.move_to(0, 1)
       button_press_count += 1
       lcd.putstr(f"pressed {button_press_count}")

    if flash_timer > 0:
       flash_timer -= 1
       led_value = 1 if (flash_timer % 2) != 0 else 0
    else:
       led_value = 0
   
    red_led.value(led_value)
   

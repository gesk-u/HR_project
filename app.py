from machine import Pin, PWM, I2C, ADC
from ssd1306 import SSD1306_I2C
from fifo import Fifo
import time
from piotimer import Piotimer
from led import Led

OPTIONS = ("Measure HR", "Basic HRV", "Coffee", "Kubios", "History")

class App():
    def __init__(self, oled, rot, hr_sensor):
        self.oled = oled
        self.rot = rot
        self.hr_sensor = hr_sensor
    def run(self):
        pass

hr_sensor = hr_fifo(250, 27)
tmr = Piotimer(mode = Piotimer.PERIODIC, freq = 250, callback = hr_sensor.handler)
rot = Rotary_encoder(30, 10, 11, 12)              
oled = OLED(128, 64)
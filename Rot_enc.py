from machine import Pin, PWM, I2C
from ssd1306 import SSD1306_I2C
from fifo import Fifo
import time

class Rotary_encoder:
    def __init__(self, pin_a, pin_b, pin_push, fifo):
        self.a = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self.b = Pin(pin_b, Pin.IN, Pin.PULL_UP)
        self.push = Pin(pin_push, Pin.IN, Pin.PULL_UP)
        self.last_rot_time = 0
        self.fifo = fifo
        self.last_push_time = 0
        
        self.a.irq(handler=self.handler_rotate, trigger=Pin.IRQ_FALLING, hard=True)
        self.push.irq(handler=self.handler_push, trigger=Pin.IRQ_FALLING, hard=True)

    def handler_rotate(self, pin):
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_push_time) > 50:
            if self.b.value() == 1:
                self.fifo.put(1)
            else:                      
                self.fifo.put(2)
            self.last_rot_time = now
            
    def handler_push(self, pin):
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_push_time) > 350:
            self.fifo.put(0)
            self.last_push_time = now
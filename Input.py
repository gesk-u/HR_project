
from machine import Pin, ADC
from fifo import Fifo
import time


# ---------------------------------------------------------------------------
# Btn — generic push-button with debounce
# ---------------------------------------------------------------------------

class Btn:
    def __init__(self, pin_nr):
        self.pin = Pin(pin_nr, Pin.IN, Pin.PULL_UP)
        self.fifo = Fifo(10)
        self.last_time = 0
        self.pin.irq(trigger=Pin.IRQ_FALLING, handler=self._handler)

    def _handler(self, pin):
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_time) > 250:
            self.fifo.put(3)
            self.last_time = now     


# ---------------------------------------------------------------------------
# Rotary_encoder — interrupt-driven rotary encoder + push button
# ---------------------------------------------------------------------------

class Rotary_encoder(Fifo):
    '''
    Rotation events are pushed onto rot_fifo  (1 = CW, 2 = CCW).
    Button press events are pushed onto push_fifo (always 0).
 
    Debounce intervals prevent false triggers:
      - 150 ms for rotation
      - 350 ms for the button
    '''

    def __init__(self, memory, pin_a, pin_b, pin_push):
        '''
        Args:
            memory  : FIFO buffer size (parent class).
            pin_a   : Encoder channel A GPIO pin.
            pin_b   : Encoder channel B GPIO pin (read to determine direction).
            pin_push: Push-button GPIO pin.
        '''

        super().__init__(memory)
        self._a = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self._b = Pin(pin_b, Pin.IN, Pin.PULL_UP)
        self.rot_fifo = Fifo(30)
        self.push_fifo = Fifo(30)
        self._push = Pin(pin_push, Pin.IN, Pin.PULL_UP)
        self._last_rot_time = 0
        self._last_push_time = 0
        self._a.irq(handler=self.handler_rotate, trigger=Pin.IRQ_FALLING, hard=True)
        self._push.irq(handler=self.handler_push, trigger=Pin.IRQ_FALLING, hard=True)

    def handler_rotate(self, pin):
        '''
        IRQ handler for encoder rotation 
 
          B = 1 → clockwise      → push 1
          B = 0 → counter-clockwise → push 2
        '''

        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_rot_time) > 150:
            if self._b.value():
                self.rot_fifo.put(1)
            else:
                self.rot_fifo.put(2)
                print("handler2")
            self._last_rot_time = now

    def handler_push(self, pin):
        '''
        IRQ handler for the push button
 
        Pushes 0 onto push_fifo after a 350 ms debounce window.
        '''

        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_push_time) > 350:
            self.push_fifo.put(0)
            print("done")
            self._last_push_time = now

        
# ---------------------------------------------------------------------------
# HR_sensor — ADC reader with interrupt-driven FIFO buffering
# ---------------------------------------------------------------------------
 
class HR_sensor(Fifo):
    '''
    Reads raw ADC samples from the PPG sensor at a fixed rate.
 
    Inherits from Fifo so that the timer ISR can push samples into the buffer
    without blocking the main loop.
    '''

    def __init__(self, size, adc_pin):
        '''
        Args:
        size   : FIFO capacity (number of samples to buffer).
        adc_pin: GPIO pin number connected to the PPG sensor output.
        '''
        super().__init__(size)
        self.av = ADC(adc_pin)
        self.dbg = Pin(0, Pin.OUT)
        self.val = 0                # Most recent raw reading

    def handler(self, tid):
        '''
        Piotimer called at the configured sample rate.
 
        Reads one ADC sample and pushes it into the FIFO.
        If the FIFO is full, the oldest sample is discarded to make room.
        '''

        self.val = self.av.read_u16()
        try:
            self.put(self.val)
        except:
            self.get()          # Drop oldest sample
            self.put(self.val)
        self.dbg.toggle()


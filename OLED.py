from machine import Pin, PWM, I2C, ADC
from ssd1306 import SSD1306_I2C
from fifo import Fifo
import time
from piotimer import Piotimer
from led import Led

HEART = [
    [0,0,1,0,1,0,0,0,0],
    [0,0,0,0,0,0,0,0,0],
    [0,1,1,1,1,1,1,0,0],
    [0,1,0,0,0,1,0,1,0],
    [0,1,0,0,0,1,0,1,0],
    [0,1,0,0,0,1,0,0,0],
    [0,1,1,1,1,1,0,0,0],
    [0,0,1,1,1,0,0,0,0],
    [0,0,0,0,0,0,0,0,0],
]

class hr_fifo(Fifo):

    def __init__(self, size, adc_pin):
        super().__init__(size)
        self.av = ADC(adc_pin)
        self.dbg = Pin(0, Pin.OUT)

        self.history = []
        self.MAX_HISTORY = 200
        
        self.beats = []
        self.MAX_BEATS = 30

        self.beat = False
        self.bpm = None
        self.last_y = 0
        self.led = Led(22, mode=Pin.OUT, brightness=1)
        self.PPI = []

    def handler(self, tid):
        val = self.av.read_u16()
        try:
            self.put(val)
        except:
            self.get()
            self.put(val)
        self.dbg.toggle()


    def run(self, oled, rot_turn):
        while self.has_data():
            
            val = self.get()

            self.history.append(val)
            if len(self.history) > self.MAX_HISTORY:
                self.history.pop(0)

            min_v = min(self.history)
            max_v = max(self.history)

            threshold_on  = (min_v + max_v * 3) // 4
            threshold_off = (min_v + max_v) // 2

            if val > threshold_on and not self.beat:
                self.beat = True
                self.beats.append(time.ticks_ms())
                if len(self.beats) > self.MAX_BEATS:
                    self.beats.pop(0)
                self.bpm = self.calculate_bpm()
                self.calculate_ppi()
                self.led.on()

            if val < threshold_off and self.beat:
                self.beat = False
                self.led.off()
            y = self.last_y
            self.refresh(val, min_v, max_v)
            oled.hr_animation(y, self.last_y, self.bpm, self.beat)
            

    def calculate_bpm(self):
        if len(self.beats) >= 2:
            beat_time = time.ticks_diff(self.beats[-1], self.beats[0]) / 1000
            if beat_time > 0:
                intervals = len(self.beats) - 1 
                return int((intervals / beat_time) * 60)
        return None
    
    def calculate_ppi(self):
        if self.bpm:
            PPI_val = 60000 // self.bpm
            self.PPI.append(PPI_val)
            print(self.PPI)

    def refresh(self, val, min_v, max_v):
        if max_v - min_v > 0:
            y = 64 - int(32 * (val - min_v) / (max_v - min_v))
            self.last_y = y


class Rotary_encoder(Fifo):
    def __init__(self, memory, pin_a, pin_b, pin_push):
        super().__init__(memory)
        self.a = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self.b = Pin(pin_b, Pin.IN, Pin.PULL_UP)
        self.push = Pin(pin_push, Pin.IN, Pin.PULL_UP)
        self.last_rot_time = 0
        self.last_push_time = 0
        
        self.a.irq(handler=self.handler_rotate, trigger=Pin.IRQ_FALLING, hard=True)
        self.push.irq(handler=self.handler_push, trigger=Pin.IRQ_FALLING, hard=True)

    def handler_rotate(self, pin):
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_rot_time) > 50:
            if self.b.value() == 1:
                print("handler1")
                self.put(1)
            else:                      
                self.put(2)
                print("handler2")
            self.last_rot_time = now
            
    def handler_push(self, pin):
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_push_time) > 350:
            self.put(0)
            self.last_push_time = now

class Menu:
    @property
    def selected_index(self):
        return (self.y_arrow - self.titl_opt_dis) // self.opt_dis
    
    def __init__(self, title_size, title = "Menu", arrow = ">"):
        self.title = title
        self.title_size = title_size
        self.titl_opt_dis = self.title_size + 8
        
        self.arrow = arrow
        self.x_arrow = 0
        self.y_arrow = None
        
        self.options = []
        self.opt_dis = 8
        self.dist_opt_arrow = 8
        
    def add_options (self, *options):
        self.options = list(options)
        
    def update_arrow(self, rot_turn):
        min_y = self.titl_opt_dis
        max_y = self.titl_opt_dis + self.opt_dis * (len(self.options) - 1)
        # DOWN
        if rot_turn == 1:
            if self.y_arrow < max_y:
                self.y_arrow += self.opt_dis
        # UP
        elif rot_turn == 2:
            if self.y_arrow > min_y:
                self.y_arrow -= self.opt_dis
        

class OLED:
    
    def __init__(self, width, height):
        
        self.width = width
        self.height = height

        self.i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
        self.oled = SSD1306_I2C(self.width, self.height, self.i2c)
        
        self.menu = Menu(8)
        
    
        

    def show_menu(self, rot_turn, *options):
        self.menu.add_options(*options)
        self.menu.titl_opt_dis = self.menu.title_size + 8
        self.menu.opt_dis = (self.height - self.menu.titl_opt_dis) // len(self.menu.options)

        if self.menu.y_arrow is None:               # fixed: initialise arrow to first option
            self.menu.y_arrow = self.menu.titl_opt_dis
        
        self.menu.update_arrow(rot_turn)
        
        self.oled.fill(0)
        
        for i, option in enumerate(self.menu.options):
            y = self.menu.titl_opt_dis + self.menu.opt_dis * i
            self.oled.text(option, self.menu.dist_opt_arrow, y, 1)
        
        self.oled.text(
            self.menu.arrow,
            self.menu.x_arrow,
            self.menu.y_arrow, 1
        )
        self.oled.show()
    
        
                
                
    def enter_option(self):
        self.oled.fill(0)
        print(self.menu.selected_index)
        #if self.menu.selected_index == 0:
            #hr_animation(hr_last_)
        
        
    def hr_animation(self, hr_last_y, hr_y, bpm, beat):
        self.oled.vline(0, 0, 64, 0)
        self.oled.scroll(-1, 0)
        
        self.oled.line(125, hr_last_y, 126, hr_y, 1)
        
        self.oled.fill_rect(0, 0, 128, 32, 0)
        
        if bpm is not None:
            self.oled.text("%d bpm" % bpm, 12, 0)

        if beat:
            for row_i, row in enumerate(HEART):
                for col_i, c in enumerate(row):
                    self.oled.pixel(col_i, row_i, c)
                    
        self.oled.show()
        
    def calc_rmmds(self, values):
        newvals = []
        cur_val = 0
        for i in range(len(values)):
            if i < (len(values) - 1):
                value = values[i]
                print(value)
                value = values[i+1] - values[i]
                
                value = value**2
                newvals.append(value)
            
        #print(newvals)
        RMMSD = sum(newvals)/len(newvals)
        print(RMMSD)

            
hr_sensor = hr_fifo(250, 27)
OPTIONS = ("Measure HR", "Basic HRV", "Coffee", "Kubios", "History")
tmr = Piotimer(mode = Piotimer.PERIODIC, freq = 250, callback = hr_sensor.handler)

rot = Rotary_encoder(30, 10, 11, 12)              
oled = OLED(128, 64)

oled.show_menu(0, *OPTIONS)
while True:
    if rot.has_data():
        rot_turn = rot.get()
        print("rot_turn:", rot_turn)
        
        if rot_turn == 0:
            idx = oled.menu.selected_index
            print("Selected:", OPTIONS[idx])
            oled.enter_option()
            if oled.menu.selected_index == 0:
                y = hr_sensor.last_y
                hr_sensor.run(oled, rot_turn)
                if rot_turn == 0:
                    oled.show_menu(rot_turn, *OPTIONS)
                #oled.hr_animation(hr_sensor.last_y, y, hr_sensor.bpm, hr_sensor.beat)
                
        else:
            oled.show_menu(rot_turn, *OPTIONS)
        
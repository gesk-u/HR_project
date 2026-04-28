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


class HR_sensor(Fifo):
    def __init__(self, size, adc_pin):
        super().__init__(size)
        self.av = ADC(adc_pin)
        self.dbg = Pin(0, Pin.OUT)
        self.val = 0
        
    def handler(self, tid):
        self.val = self.av.read_u16()
        try:
            self.put(self.val)
        except:
            self.get()
            self.put(self.val)
        self.dbg.toggle()
        

class Data():

    def __init__(self, hr_sensor):
        
        self.av = hr_sensor
        
        self.history = []
        self.MAX_HISTORY = 270
        self.sample = 0
        
        self.max_sample = 0
        self.min_sample = 0
        self.threshold_on = 0
        self.threshold_off = 0
        
        self.beats = []
        self.MAX_BEATS = 20
        self.beat = False
        self.MIN_BEAT_INTERVAL = 300
        self.MAX_BEAT_INTERVAL = 1500
        self.last_beat_time = 0 
        self.avg_ppi_interval = 0
        
        self.bpm = None
        self.last_y = 0
        
        self.led = Led(22, mode=Pin.OUT, brightness=1)
        
        self.mean_ppi = 0
        self.RMMDS = []
        self.ppi_list = []

        self.smooth_buf = []
        self.SMOOTH_WINDOW = 4
        self.last_beat_time = 0  
    
    # Removes old values from full list
    def if_full(self, l, max_l):
        if len(l) > max_l:
            l.pop(0)

    def run(self, oled, rot_turn):
        while self.av.has_data():
            
            self.sample = self.av.get()

            self.history.append(self.sample)
            
            self.if_full(self.history, self.MAX_HISTORY)

            self.max_sample = max(self.history)
            self.min_sample = min(self.history)

            self.threshold_on  = (self.min_sample + self.max_sample * 3) // 4
            self.threshold_off = (self.min_sample + self.max_sample) // 2

            if self.sample > self.threshold_on and not self.beat:
                now = time.ticks_ms()
                if time.ticks_diff(now, self.last_beat_time) > self.MIN_BEAT_INTERVAL:
                    self.beat = True
                    self.last_beat_time = now
                    self.beats.append(now)
                    self.if_full(self.beats, self.MAX_BEATS)
                
                    
                if self.calculate_bpm():
                    self.bpm = self.calculate_bpm()
                self.calculate_ppi()
                if len(self.ppi_list) % 50 == 0:
                    self.calc_rmmds()
                self.led.on()

            if self.sample < self.threshold_off and self.beat:
                self.beat = False
                self.led.off()
                
            y = self.last_y
            #print("Low", min_v)
            #print("Hight", max_v)
            self.refresh()
            print(self.last_y)
            oled.hr_animation(y, self.last_y, self.bpm, self.beat)
         
            

    def calculate_ppi(self):
        if len(self.beats) > 3:
            self.ppi_list = []
            for i in range(len(self.beats) - 1):
                diff = time.ticks_diff(self.beats[i+1], self.beats[i])
                
                if self.MIN_BEAT_INTERVAL < diff < self.MAX_BEAT_INTERVAL:
                    self.ppi_list.append(diff)
                if self.ppi_list:
                    self.mean_ppi = sum(self.ppi_list) / len(self.ppi_list)

    def calculate_bpm(self):
        if self.mean_ppi:
            self.bpm = 60000 / self.mean_ppi


            
    def calc_rmmds(self):
        ppi_diffs = []
        for i in range(len(self.ppi_list) - 1): 
            ppi_diff = self.ppi_list[i+1] - self.ppi_list[i]
            ppi_diffs.append(ppi_diff)
 
        ppi_sqr = []
        for d in ppi_diffs:
            #if abs(d) < 25:
            ppi_sqr.append(d**2)

        if ppi_sqr:
            #print(newvals)
            rmmds = (sum(ppi_sqr) / len(ppi_sqr)) ** 0.5

            self.RMMDS.append(int(rmmds))
            self.if_full(self.RMMDS, 10)
            print("RMMDS", self.RMMDS)
            
    def calc_sdnn(self):
        cut_PPI = self.PPI[10:]
        cleaned_PPI = []
        print("PPI", self.PPI)
        
        for i in range(len(cut_PPI) - 1):
            if abs(cut_PPI[i+1] - cut_PPI[i]) < 400:
                cleaned_PPI.append(cut_PPI[i])
            elif not cut_PPI:
                cleaned_PPI.append(p)
        print("clean PPI", cleaned_PPI)
        
        mean = sum(cleaned_PPI) / len(cleaned_PPI)
        
        for i in range(len(cleaned_PPI) - 1): 
            diff = cleaned_PPI[i+1] - mean
            diffs.append(diff)
            
        newvals = []
        for d in diffs:
            #if abs(d) < 25:
            newvals.append(d**2)
            
        print(newvals)
        if newvals:
            print(newvals)
            SDNN = (sum(newvals) / len(newvals)) ** 0.5

            self.SDNN.append(int(sdnn))
            print("SDNN", self.SDNN)
            print("PPI", self.PPI)

    def refresh(self):
        if self.max_sample - self.min_sample > 0:
            print("True")
            smoothed = self.smooth() 
            self.last_y = 64 - int(32 * (smoothed - self.min_sample) / (self.max_sample - self.min_sample))
            
    
    def smooth(self):
        self.smooth_buf.append(self.sample)
        if len(self.smooth_buf) > self.SMOOTH_WINDOW:
             self.smooth_buf.pop(0)
        return sum(self.smooth_buf) // len(self.smooth_buf)


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
        

av = HR_sensor(250, 27)
data = Data(av)
OPTIONS = ("Measure HR", "Basic HRV", "Coffee", "Kubios", "History")
tmr = Piotimer(mode = Piotimer.PERIODIC, freq = 250, callback = av.handler)

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
                y = data.last_y
                data.run(oled, rot_turn)
                if rot_turn == 0:
                    oled.show_menu(rot_turn, *OPTIONS)
                #oled.hr_animation(hr_sensor.last_y, y, hr_sensor.bpm, hr_sensor.beat)
                
        else:
            oled.show_menu(rot_turn, *OPTIONS)
        
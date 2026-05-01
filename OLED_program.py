from machine import Pin, PWM, I2C, ADC
from ssd1306 import SSD1306_I2C
from fifo import Fifo
import time
from piotimer import Piotimer
from led import Led
#time.localtime
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

POWER = [
    [0,0,0,1,0,0,0],
    [0,1,0,1,0,1,0],
    [1,0,0,1,0,0,1],
    [1,0,0,1,0,0,1],
    [1,0,0,0,0,0,1],
    [0,1,0,0,0,1,0],
    [0,0,1,1,1,0,0]
]

class Kubios:
    def __init___(self, wifi_name, wifi_password):
        pass

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

    def __init__(self, hr_sensor, sampling_rate=250):
        
        self.av = hr_sensor
        self.sampling_rate = sampling_rate
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
        self.MIN_BEAT_INTERVAL = 400
        self.MAX_BEAT_INTERVAL = 1200
        self.last_beat_time = 0 
        self.avg_ppi_interval = 0
        
        self.bpm = None
        self.bpm_list = []
        self.mean_bpm = 0
        self.last_y = 0
        
        self.led = Led(22, mode=Pin.OUT, brightness=1)
        
        self.mean_ppi = 0
        self.RMMDS = 0
        self.SDNN = 0
        self.ppi_list = []

        self.smooth_buf = []
        self.SMOOTH_WINDOW = 6
        self.last_beat_time = 0
        
    def get_data(self):
        t = time.localtime()
        timestamp = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])
        return {
            "Time": timestamp,
            "Mean PPI": self.mean_ppi,
            "Mean BPM": self.mean_bpm,
            "RMMDS": self.RMMDS,
            "SDNN": self.SDNN
            }
    # Removes old values from full list
    def if_full(self, l, max_l):
        if len(l) > max_l:
            l.pop(0)

    def run(self, oled):
        for _ in range(50):
            if self.av.has_data():
                self.sample = self.av.get()
                self.sample = self.smooth()    
                #self.sample = self.filte.process(self.sample)
                self.history.append(self.sample)
                self.if_full(self.history, self.MAX_HISTORY)

                self.max_sample = max(self.history)
                #print("MAx sample", self.max_sample)
                self.min_sample = min(self.history)
                #print("Min sample", self.min_sample)

                self.threshold_on  = (self.min_sample + self.max_sample * 3) // 4
                self.threshold_off = (self.min_sample + self.max_sample) // 2

                if self.sample > self.threshold_on and not self.beat:
                    now = time.ticks_ms()
                    if self.last_beat_time == 0:
                        self.last_beat_time = now
                    diff = time.ticks_diff(now, self.last_beat_time)
                    self.beat = True
                    self.last_beat_time = now
                    self.beats.append(now)
                    self.if_full(self.beats, self.MAX_BEATS)
                    
                        
                    if self.calculate_bpm():
                        self.bpm = self.calculate_bpm()
                    self.calculate_ppi()
                    if len(self.ppi_list) / 15 >= 1:
                        print(self.get_data())
                        self.calc_rmmds()
                        self.calc_sdnn()
                    self.led.on()

                if self.sample < self.threshold_off and self.beat:
                    self.beat = False
                    self.led.off()
                    
                y = self.last_y
                self.refresh()
                #print(self.last_y)
                oled.hr_animation(y, self.last_y, self.bpm, self.beat)
                
            
        
            

    def calculate_ppi(self):
        if len(self.beats) < 3:
            return
            #print("PPI", len(self.ppi_list))
            
        diff = time.ticks_diff(self.beats[-1], self.beats[-2])
        print("DIFF ppi", diff)
        if self.MIN_BEAT_INTERVAL < diff < self.MAX_BEAT_INTERVAL:
            self.ppi_list.append(diff)
            self.if_full(self.ppi_list, 20)
            #print(len(self.ppi_list))
            print("ppi_List", self.ppi_list)
            if len(self.ppi_list) >= 15:
                self.clean_ppi_list()
            self.mean_ppi = sum(self.ppi_list) / len(self.ppi_list)

    def clean_ppi_list(self, max_change_percent=0.25):
        if not self.ppi_list or len(self.ppi_list) < 2:
            return self.ppi_list
        
        
        sorted_ppis = sorted(self.ppi_list)
        median_ppi = sorted_ppis[len(sorted_ppis) // 2]
        
        
        clean_list = []
        start_idx = 0
    
        for i in range(len(self.ppi_list)):
            if abs(self.ppi_list[i] - median_ppi) / median_ppi <= max_change_percent:
                clean_list.append(self.ppi_list[i])
                start_idx = i + 1
                break

        if not clean_list:
            clean_list = [median_ppi]
            start_idx = 0

        
        for i in range(start_idx, len(self.ppi_list)):
            prev_beat = clean_list[-1]
            current_beat = self.ppi_list[i]

            
            change = abs(current_beat - prev_beat) / prev_beat

            if change <= max_change_percent:
                clean_list.append(current_beat)
            else:
                print(f"Artifact detected and removed: {current_beat}ms")
            
        
        self.ppi_list = clean_list
        

    def calculate_bpm(self):
        if self.mean_ppi:
            self.bpm = 60000 / self.mean_ppi
            self.bpm_list.append(self.bpm)
        if self.bpm_list:
            self.mean_bpm = sum(self.bpm_list) // len(self.bpm_list)
 

            
    def calc_rmmds(self):
        
        ppi_diffs = []
        for i in range(len(self.ppi_list) - 1): 
            ppi_diff = self.ppi_list[i+1] - self.ppi_list[i]
            ppi_diffs.append(ppi_diff)
 
        ppi_sqr = []
        for d in ppi_diffs:
            ppi_sqr.append(d**2)

        if ppi_sqr:
            rmmds = (sum(ppi_sqr) / len(ppi_sqr)) ** 0.5

            self.RMMDS = int(rmmds)
            
    def calc_sdnn(self):
        
        mean = sum(self.ppi_list) / len(self.ppi_list)
        
        ppi_diffs = []
        for i in range(len(self.ppi_list) - 1): 
            diff = self.ppi_list[i+1] - mean
            ppi_diffs.append(diff)
            
        ppi_sqr = []
        for d in ppi_diffs:
            ppi_sqr.append(d**2)
            
        if ppi_sqr:
            sdnn = (sum(ppi_sqr) / len(ppi_sqr)) ** 0.5
            self.SDNN = int(sdnn)
            #print("SDNN", self.SDNN)
            #print("PPI", self.PPI)

    def refresh(self):
        if self.max_sample - self.min_sample > 0:
            smoothed = self.smooth() 
            self.last_y = 64 - int(32 * (self.sample - self.min_sample) / (self.max_sample - self.min_sample))
            
    
    def smooth(self):
        self.smooth_buf.append(self.sample)
        if len(self.smooth_buf) > self.SMOOTH_WINDOW:
             self.smooth_buf.pop(0)
        return sum(self.smooth_buf) // len(self.smooth_buf)

    def reset(self):
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
        self.MIN_BEAT_INTERVAL = 500
        self.MAX_BEAT_INTERVAL = 1200
        self.last_beat_time = 0 
        self.avg_ppi_interval = 0
        
        self.bpm = None
        self.bpm_list = []
        self.mean_bpm = 0
        self.last_y = 0
        
        self.mean_ppi = 0
        self.RMMDS = []
        self.ppi_list = []

        self.smooth_buf = []
        self.last_beat_time = 0



class Rotary_encoder(Fifo):
    def __init__(self, memory, pin_a, pin_b, pin_push):
        super().__init__(memory)
        self.a = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self.b = Pin(pin_b, Pin.IN, Pin.PULL_UP)
        self.rot_fifo = Fifo(30)
        self.push_fifo = Fifo(30)
        self.push = Pin(pin_push, Pin.IN, Pin.PULL_UP)
        self.last_rot_time = 0
        self.last_push_time = 0
        
        self.a.irq(handler=self.handler_rotate, trigger=Pin.IRQ_FALLING, hard=True)
        self.push.irq(handler=self.handler_push, trigger=Pin.IRQ_FALLING, hard=True)

    def handler_rotate(self, pin):
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_rot_time) > 50:
            if self.b.value():
                #print("handler1")
                self.rot_fifo.put(1)
            else:                      
                self.rot_fifo.put(2)
                print("handler2")
            self.last_rot_time = now
            
    def handler_push(self, pin):
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_push_time) > 350:
            self.push_fifo.put(0)
            print("done")
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
        
        for row_i, row in enumerate(POWER):
            for col_i, c in enumerate(row):
                self.oled.pixel(col_i + 74, row_i + 56, c)
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
        
    def intro_anim(self, push_fifo=None):
        with open('intro.py', 'r') as f:
            exec(f.read())
            
        for row_i, row in enumerate(LOGOSTART):
            for col_i, c in enumerate(row):
                self.oled.pixel(col_i + 51, row_i + 10, c)
            self.oled.show()
        
        
        for i in range(len(HEARTS) - 1):
            if push_fifo and push_fifo.has_data():
                push_fifo.get()
                return True


            for row_i, row in enumerate(HEARTS[i]):
                for col_i, c in enumerate(row):
                    self.oled.pixel(col_i, row_i, c)
            self.oled.show()

            time.sleep(INTRODELAY)

        return False
                    
    def quit(self):
        self.oled.fill(0)
        self.oled.show()
        raise SystemExit
        

class App:
    def __init__(self, delay_time, oled, data, rot, kubios, mqtt, history):
        self.delay = delay_time
        self.oled = oled
        self.data = data
        self.rot = rot
        self.kubios = kubios
        self.mqtt = mqtt
        self.history = history
        self.option = 0
        self.rot_change = None
        self.btn_val = False
        self.state = 0
    
    def check_btn_press(self):
        if self.rot.push_fifo.has_data():
            self.change = self.rot.push_fifo.get()
            if self.change == 0:
                if self.btn_val == 0:
                    self.btn_val = 1
                else:
                    self.btn_val = 0
            else:
                while self.rot.push_fifo.has_data():
                    self.rot.push_fifo.get()

        return self.btn_val
    
    def _change_menu(self):
        rot_turn = self.rot.rot_fifo.get()
        print(rot_turn)
        self.oled.show_menu(rot_turn, *OPTIONS)
        if self.check_btn_press():
            self.btn_val = False
            self.option = self.oled.menu.selected_index
            print("Selected:", self.option)

    def state_off(self):
        self.oled.oled.fill(0)
        self.oled.oled.show()

    def anim_state(self):
        interrupted = self.oled.intro_anim(push_fifo=self.rot.push_fifo)
        if interrupted:
            self.btn_val = False
            self.state = 2

    
    def first_menu(self):
        self.oled.show_menu(0, *OPTIONS)
    
    def state_menu(self):
        while self.rot.rot_fifo.has_data():
            self._change_menu()

    def change_option_state(self):
        if self.option == 0:
            self.state = 3
        elif self.option == 1:
            self.state = 6
        elif self.option == 2:
            self.state = 5
        elif self.option == 3:
            self.state = 6
        elif self.option == 4:
            self.state = 7
        elif self.option == 5:
            self.state = 8
    # TODO Will ask user to put finger and wait
    def state_3a(self):
        app.state = 4
    def state_3b(self):
        app.data.run(self.oled)
    #TODO  returns results
    def state_3c(self):
        pass

        
        
    
kubios = 0
mqtt = 0   
history = 0
    
av = HR_sensor(250, 27)
data = Data(av)
OPTIONS = ("Measure HR", "Basic HRV", "Coffee", "Kubios", "History", "Shutdown")
tmr = Piotimer(mode = Piotimer.PERIODIC, freq = 250, callback = av.handler)

rot = Rotary_encoder(30, 10, 11, 12)              
oled = OLED(128, 64)
app = App(0.05, oled, data, rot, kubios, mqtt, history)
#oled.intro_anim(rot)
#app.state = 2
oled.show_menu(0, *OPTIONS)
while True:
    # Turned off
    if app.state == 0:
        app.state_off()
        if app.check_btn_press():
            app.btn_val = False
            app.state = 1
    # animation 
    if app.state == 1:
        app.anim_state()
        if app.check_btn_press():
            app.btn_val = False
            app.state = 2
    # Menu
    elif app.state == 2:
        app.first_menu()
        while True:
            app.state_menu()
            if app.check_btn_press():
                app.btn_val = False
                app.state_off()
                app.change_option_state()
                app.data.reset()
                break
    elif app.state == 3:
        app.state_3a()
    elif app.state == 4:
        while True:
            app.state_3b()
            if app.check_btn_press():
                app.btn_val = False
                app.state = 2
                break



























'''if rot.push_fifo.has_data():
    rot_turn = rot.push_fifo.get()
    if rot.rot_fifo.has_data():
        rot_rot = rot.rot_fifo.get()
        
    print("rot_turn:", rot_turn)
    
    if rot_turn == 0:
        idx = oled.menu.selected_index
        print("Selected:", OPTIONS[idx])
        oled.enter_option()
        if oled.menu.selected_index == OPTIONS.index("Measure HR"):
            y = data.last_y
            data.run(oled, rot_turn)
            print(data.get_data())
            if rot_turn == 0:
                oled.show_menu(rot_turn, *OPTIONS)
            #oled.hr_animation(hr_sensor.last_y, y, hr_sensor.bpm, hr_sensor.beat)
        if oled.menu.selected_index == OPTIONS.index("Shutdown"):
            oled.quit()
            
    else:
        oled.show_menu(rot_rot, *OPTIONS)'''
        
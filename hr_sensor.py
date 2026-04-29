from machine import Pin, PWM, I2C, ADC
from fifo import Fifo
from led import Led
import time



class hr_fifo(Fifo):

    def __init__(self, size, adc_pin):
        super().__init__(size)
        self.av = ADC(adc_pin)
        self.dbg = Pin(0, Pin.OUT)

        self.history = []
        self.MAX_HISTORY = 200
        
        self.beats = []
        self.MAX_BEATS = 20

        self.beat = False
        self.bpm = None
        self.last_y = 0
        self.led = Led(22, mode=Pin.OUT, brightness=1)
        self.PPI = []
        self.RMMDS = []
        self.smooth_buf = []
        self.SMOOTH_WINDOW = 4 

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
                    
                if self.calculate_bpm():
                    self.bpm = self.calculate_bpm()
                self.calculate_ppi()
                if len(self.PPI) % 50 == 0:
                    self.calc_rmmds()
                self.led.on()

            if val < threshold_off and self.beat:
                self.beat = False
                self.led.off()
                
            y = self.last_y
            self.refresh(val, min_v, max_v)
            oled.hr_animation(y, self.last_y, self.bpm, self.beat)
         
            

    def calculate_bpm(self):
        if len(self.beats) > 3:
            
            diffs = []
            for i in range(len(self.beats) - 1):
                diff = time.ticks_diff(self.beats[i+1], self.beats[i])
            
                if 450 < diff < 2000:
                    diffs.append(diff)
            if not diffs:
                return None
                
            avg_interval = sum(diffs) / len(diffs)
            
            bpm = 60000 / avg_interval
            return bpm
            #if beat_time > 0:
                #intervals = len(self.beats) - 1 
                #return int((intervals / beat_time) * 60)
        return None
    
    def calculate_ppi(self):
        if self.bpm:
            PPI_val = 60000 // self.bpm
            self.PPI.append(PPI_val)
            
            print("len ppi", len(self.PPI))
            
            
    def calc_rmmds(self):
        cut_PPI = self.PPI[10:]
        cleaned_PPI = []
        #print("PPI", self.PPI)
        
        for i in range(len(cut_PPI) - 1):
            if abs(cut_PPI[i+1] - cut_PPI[i]) < 400:
                cleaned_PPI.append(cut_PPI[i])
            elif not cut_PPI:
                cleaned_PPI.append(p)
        #print("clean PPI", cleaned_PPI)
        diffs = []
        
        for i in range(len(cleaned_PPI) - 1): 
            diff = cleaned_PPI[i+1] - cleaned_PPI[i]
            diffs.append(diff)
            
    
        #mean = sum(abs(d) for d in diffs) / len(diffs)
        #variance = sum((abs(d) - mean) ** 2 for d in diffs) / len(diffs)
        #std = variance ** 0.5
        #threshold = mean + 2 * std
        #print("threshold", threshold)  
        newvals = []
        for d in diffs:
            #if abs(d) < 25:
            newvals.append(d**2)
    
        #print("filtered out:", [d for d in diffs if abs(d) >= threshold])    
        #print(newvals)
        if newvals:
            #print(newvals)
            rmmds = (sum(newvals) / len(newvals)) ** 0.5

            self.RMMDS.append(int(rmmds))
            #print("RMMDS", self.RMMDS)
            #print("PPI", self.PPI)
            
    def calc_sdnn(self):
        cut_PPI = self.PPI[10:]
        cleaned_PPI = []
        #print("PPI", self.PPI)
        
        for i in range(len(cut_PPI) - 1):
            if abs(cut_PPI[i+1] - cut_PPI[i]) < 400:
                cleaned_PPI.append(cut_PPI[i])
            elif not cut_PPI:
                cleaned_PPI.append(p)
        #print("clean PPI", cleaned_PPI)
        
        mean = sum(cleaned_PPI) / len(cleaned_PPI)
        
        for i in range(len(cleaned_PPI) - 1): 
            diff = cleaned_PPI[i+1] - mean
            diffs.append(diff)
            
        newvals = []
        for d in diffs:
            #if abs(d) < 25:
            newvals.append(d**2)
            
        #print(newvals)
        if newvals:
            #print(newvals)
            SDNN = (sum(newvals) / len(newvals)) ** 0.5

            self.SDNN.append(int(sdnn))
            #print("SDNN", self.SDNN)
            #print("PPI", self.PPI)

    def refresh(self, val, min_v, max_v):
        if max_v - min_v > 0:
            smoothed = self.smooth(val)  
            y = 64 - int(32 * (smoothed - min_v) / (max_v - min_v))
            self.last_y = y
    
    def smooth(self, val):
        self.smooth_buf.append(val)
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
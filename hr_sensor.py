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

    def refresh(self, val, min_v, max_v):
        if max_v - min_v > 0:
            y = 64 - int(32 * (val - min_v) / (max_v - min_v))
            self.last_y = y

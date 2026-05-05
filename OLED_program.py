from machine import Pin, PWM, I2C, ADC
from ssd1306 import SSD1306_I2C
from fifo import Fifo
import time
from piotimer import Piotimer
from led import Led
from umqtt.simple import MQTTClient
import network
import ubinascii
import json

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

class Client:
    def __init__(self):
        self.name = None


    def update_user_name(self, oled):
        oled.oled.fill(0)
        oled.oled.text("NAME" + self) 

class User_input:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$ "
    NAMES = "known_names.json"

    def __init__(self):
        self.selected_name = None
        self.new_name = ""
        self.char_index = 0
        self.needs_update = False
        self.localdata = []

    def enter_name(self, rot, accept_btn, remove_btn, oled):
        if rot.rot_fifo.has_data():
            rot_turn = rot.rot_fifo.get()
            if rot_turn == 1:
                self.char_index = (self.char_index + 1) % len(self.alphabet)
            else:
                self.char_index = (self.char_index - 1) % len(self.alphabet)
            self.needs_update = True


        if rot.push_fifo.has_data():
            rot.push_fifo.get()
            self.new_name += self.alphabet[self.char_index]
            self.needs_update = True

        if accept_btn.fifo.has_data():
            accept_btn.fifo.get()
            print(f"Name accepted {self.new_name}")
            self.selected_name = self.new_name
        
        if remove_btn.fifo.has_data():
            remove_btn.fifo.get()
            self.new_name = self.new_name[:-1] 
            self.needs_update = True

        if self.needs_update:
            self.update_usrname_display(oled)

    def update_usrname_display(self, oled):
        oled.oled.fill(0)
        oled.oled.text("NEW CLIENT ", 0, 0, 1)
        oled.oled.hline(0, 10, 128, 1)
        oled.oled.text("Name:", 0, 15, 1)
        oled.oled.text(self.new_name + "_", 45, 15, 1)

        prev_c = self.alphabet[(self.char_index - 1) % len(self.alphabet)]
        curr_c = self.alphabet[self.char_index]
        next_c = self.alphabet[(self.char_index + 1) % len(self.alphabet)]

        oled.oled.text(prev_c, 30, 45, 1)
        oled.center_text(f"> {curr_c} <", 42)
        oled.oled.text(next_c, 90, 45, 1)

        oled.oled.text("Push to add", 20, 56, 1)
        oled.oled.show()
        self.needs_update = False

    def local_file(self):        
        try:
            with open('localhistory.json') as f:
                self.localdata = json.load(f)
                print("local history successfully loaded")
        except:
            with open('localhistory.json', 'w') as f:
                pass
                print("local history file missing, created it")
                
    def local_add(self, client, reading):
        self.localdata.setdefault(client, []).append(reading) #setdefault creates an empty list if the user isn't in history, to prevent errors
        
    def local_load(self, client):
        self.data = self.localdata[client]
        return self.data




class Wifi:
    def __init__(self):   
        self.selected_ssid = ""
        self.password = ""
        self.wlan = network.WLAN(network.STA_IF)
        self.mac = 0

    def get_pico_mac(self):
        mac_bytes = self.wlan.config("mac")
        self.mac = ubinascii.hexlify(mac_bytes).decode().upper()
        return self.mac

    def wifi_ana(self):
        self.selected_ssid = "Tkach"
        self.password = "Gesku0911"
    
    def default_wifi(self):
        self.selected_ssid = "KME751_Group_8"
        self.password = "TkachGrantLay"

    def wifi_on(self):
        #self.wlan.active(False)
        time.sleep_ms(100)
        self.wlan.active(True)
        print("CONF", self.selected_ssid, self.password)
        # Connect only if not already connected.
        if not self.wlan.isconnected():
            print("Connecting to Wi-Fi...")
            print("CONF", self.selected_ssid, self.password)
            self.wlan.connect(self.selected_ssid, self.password)

            # Keep waiting until the Pico successfully connects.
            while not self.wlan.isconnected():
                self.wlan.connect(self.selected_ssid, self.password)

                time.sleep_ms(250)
        print("Connected to SSID:", self.wlan.config('ssid'))
        # Show the Pico's local IP address after connection.
        print("Wi-Fi connected:", self.wlan.ifconfig()[0])
        return self.wlan

    def wifi_off(self):
        self.wlan.active(False)
class Kubios:
    BROKER_IP = "194.110.232.94"
    BROKER_PORT = 1883
    REQUEST_TOPIC = b"kubios/request"
    RESPONSE_TOPIC = b"kubios/response"
    OUTPUT_FILE = "kubios_response.json"
    TIMEOUT_MS = 15000
    
    def __init__(self):
        self.client = None
        self.latest_response = None
        
    def mqtt_client(self, mac):
        self.client = MQTTClient(
            client_id=(mac + "_ext").encode(),
            server=self.BROKER_IP, 
            port=self.BROKER_PORT)
        self.client.set_callback(self.mqtt_callback)

    def mqtt_callback(self, topic, msg):
        if topic != self.RESPONSE_TOPIC:
            return
        try:
            self.latest_response = json.loads(msg)
        except ValueError:
            self.latest_response = None

    def connect_and_subscribe(self):
        self.client.connect()
        self.client.subscribe(self.RESPONSE_TOPIC)

    def send_request(self, mac, ppi_list):
        payload = self.build_request_payload(mac, ppi_list)
        self.client.publish(self.REQUEST_TOPIC, json.dumps(payload))

    def wait_for_response(self):
        start = time.ticks_ms()

        while time.ticks_diff(time.ticks_ms(), start) < self.TIMEOUT_MS:
            self.client.check_msg()
            if self.latest_response:
                print("Response received:")
                #print(json.dumps(self.latest_response))

                self.save_json_to_pico(self.OUTPUT_FILE, self.latest_response)
                print("Saved to file:", self.OUTPUT_FILE)
                break

            time.sleep_ms(200)
        self.client.disconnect()
        print("Client disconnected")
        return self.latest_response

    def build_request_payload(self, mac_address, ppi_list):
        if ppi_list:
            return {
                "mac": mac_address,
                "type": "RRI",
                "data": ppi_list,
                "analysis": {"type": "readiness"}
            }
    def show_responce(self, oled):
        if not self.latest_response:
            oled.oled.fill(0)
            oled.center_text("No response", 28)
            oled.oled.show()
            return

        result = self.latest_response.get("data", {}).get("analysis", {})
        bpm   = result.get("mean_hr_bpm", "N/A")
        bpm = str(round(float(bpm)))
        ppi   = result.get("mean_rr_ms",  "N/A")
        ppi = str(round(float(ppi)))
        rmssd = result.get("rmssd_ms",    "N/A")
        rmssd = str(round(float(rmssd)))
        sdnn  = result.get("sdnn_ms",     "N/A")
        sdnn = str(round(float(sdnn)))
        sns   = result.get("sns_index",   "N/A")
        sns = str(round(float(sns), 3))
        pns   = result.get("pns_index",   "N/A")
        pns = str(round(float(pns), 3))

        oled.oled.fill(0)
        oled.oled.text("HR:"    + str(bpm),   0,  0, 1)
        oled.oled.text("PPI:"   + str(ppi),   0, 10, 1)
        oled.oled.text("RMSSD:" + str(rmssd), 0, 20, 1)
        oled.oled.text("SDNN:"  + str(sdnn),  0, 30, 1)
        oled.oled.text("SNS:"   + str(sns),   0, 42, 1)
        oled.oled.text("PNS:"   + str(pns),   0, 52, 1)
        oled.oled.show()



    def save_json_to_pico(self, filename, data):
        with open(filename, "w") as file:
            json.dump(data, file)

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
    HRV_TIMER = 7500

    def __init__(self, hr_sensor, sampling_rate=250):
        self.av = hr_sensor
        self.sampling_rate = sampling_rate
        self.history = []
        self.MAX_HISTORY = 500
        self.sample = 0
        self.count_sample = 0
        self.max_sample = 0
        self.min_sample = 0
        self.threshold_on = 0
        self.threshold_off = 0
        self.beats = []
        self.MAX_BEATS = 20
        self.beat = False
        self.MIN_BEAT_INTERVAL = 400
        self.MAX_BEAT_INTERVAL = 2000
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
        self.SMOOTH_WINDOW = 30
        self.last_beat_time = 0
        self.y_buffer = []

    def read(self):
        self.tmr = Piotimer(mode=Piotimer.PERIODIC, freq=self.sampling_rate, callback=self.av.handler)

    def read_off(self):
        while self.av.has_data():
            self.av.get()
        self.tmr.deinit()

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

    def if_full(self, l, max_l):
        if len(l) > max_l:
            l.pop(0)

    def hrv_mode(self, oled):
        self.median_filter()
        self.calc_rmmds()
        self.calc_sdnn()
        oled.hrv_display(self.mean_ppi, self.mean_bpm, self.RMMDS, self.SDNN)

    def hrv_history(self):
        hrv_history = self.get_data()
        return hrv_history

    def run(self, oled):
        # Removed the heavy math from outside the loop
        for _ in range(250):
            if self.av.has_data():
                self.sample = self.av.get()
                self.count_sample += 1
                self.sample = self.smooth()
                self.history.append(self.sample)
                self.if_full(self.history, self.MAX_HISTORY)
                

                if self.count_sample % 50 == 0 and len(self.history) > 100:
                    self.max_sample = max(self.history)
                    self.min_sample = min(self.history)
                    amplitude = self.max_sample - self.min_sample
                    #self.threshold_on  = (self.min_sample + self.max_sample * 3) // 4
                    self.threshold_on = self.min_sample + int(amplitude * 0.75)
                    self.threshold_off = (self.min_sample + self.max_sample) // 2

                if self.sample > self.threshold_on and not self.beat:
                    now = time.ticks_ms()
                    if self.last_beat_time == 0:
                        self.last_beat_time = now
                    diff = time.ticks_diff(now, self.last_beat_time)
                    self.beat = True

                    if self.last_beat_time == 0 or diff >= self.MIN_BEAT_INTERVAL:
                        self.last_beat_time = now
                        self.beats.append(now)
                        self.if_full(self.beats, self.MAX_BEATS)
                        
                        self.calculate_ppi()
                        self.calculate_bpm()

                        self.led.on()

                if self.sample < self.threshold_off and self.beat:
                    self.beat = False
                    self.led.off()

                self.refresh()
                #self.y_buffer.append(self.last_y)
                if self.count_sample % 10 == 0:
                    self.y_buffer.append(self.last_y)
                    oled.hr_animation(self.y_buffer, self.bpm, self.beat)
                    self.y_buffer.clear()


    def median_filter(self, max_change_percent=0.2, window_size=5):
        if not self.ppi_list or len(self.ppi_list) < 2:
            return self.ppi_list

        sorted_ppis = sorted(self.ppi_list)
        global_median = sorted_ppis[len(sorted_ppis) // 2]

        clean_list = []
        start_idx = 0

        for i in range(len(self.ppi_list)):
            if abs(self.ppi_list[i] - global_median) / global_median <= max_change_percent:
                clean_list.append(self.ppi_list[i])
                start_idx = i + 1
                break

        if not clean_list:
            clean_list = [global_median]
            start_idx = 0

        for i in range(start_idx, len(self.ppi_list)):
            current_beat = self.ppi_list[i]
            recent_beats = clean_list[-window_size:]
            temp_sorted = sorted(recent_beats)
            local_baseline = temp_sorted[len(temp_sorted) // 2]
            change = abs(current_beat - local_baseline) / local_baseline
            if change <= max_change_percent:
                clean_list.append(current_beat)
            else:
                print(f"Artifact removed: {current_beat}ms (Baseline was {local_baseline}ms, Change: {change*100:.1f}%)")

        self.ppi_list = clean_list
        return self.ppi_list

    def calculate_ppi(self):
        if len(self.beats) < 3:
            return
        diff = time.ticks_diff(self.beats[-1], self.beats[-2])
        print("DIFF ppi", diff)
        if self.MIN_BEAT_INTERVAL < diff < self.MAX_BEAT_INTERVAL:
            self.ppi_list.append(diff)
            self.if_full(self.ppi_list, 30)
            print("ppi_List", self.ppi_list)
            self.mean_ppi = sum(self.ppi_list) / len(self.ppi_list)

    def clean_ppi_list(self, max_change_percent=0.3):
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
        return self.ppi_list

    def calculate_bpm(self):
        if self.mean_ppi > 0:
            self.bpm = int(60000 / self.ppi_list[-1])
            self.mean_bpm = int(60000 / self.mean_ppi)
            '''
            self.bpm = int(60000 / self.mean_ppi)
            self.bpm_list.append(self.bpm)
            self.if_full(self.bpm_list, 30)
        if self.bpm_list:
            self.mean_bpm = sum(self.bpm_list) // len(self.bpm_list)'''

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

        ppi_sqr = []
        for ppi in self.ppi_list:
            diff = ppi - mean           
            squared = diff ** 2         
            ppi_sqr.append(squared)

        variance = sum(ppi_sqr) / (len(self.ppi_list) - 1)
        self.SDNN = int(variance ** 0.5)


   

    def refresh(self):
        if self.max_sample - self.min_sample > 0:
            self.last_y = 50 - int(32 * (self.sample - self.min_sample) / (self.max_sample - self.min_sample))

    def smooth(self):
        self.smooth_buf.append(self.sample)
        if len(self.smooth_buf) > self.SMOOTH_WINDOW:
            self.smooth_buf.pop(0)
        return sum(self.smooth_buf) // len(self.smooth_buf)

    def reset(self):
        self.history = []
        self.MAX_HISTORY = 500
        self.sample = 0
        self.count_sample = 0
        self.max_sample = 0
        self.min_sample = 0
        self.threshold_on = 0
        self.threshold_off = 0
        self.beats = []
        self.MAX_BEATS = 20
        self.beat = False
        self.MIN_BEAT_INTERVAL = 400
        self.MAX_BEAT_INTERVAL = 2000
        self.last_beat_time = 0
        self.avg_ppi_interval = 0
        self.bpm = None
        self.bpm_list = []
        self.mean_bpm = 0
        self.last_y = 0
        self.mean_ppi = 0
        self.RMMDS = 0
        self.SDNN = 0
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
        if time.ticks_diff(now, self.last_rot_time) > 150:
            if self.b.value():
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


class OLED:

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=1000000)
        self.oled = SSD1306_I2C(self.width, self.height, self.i2c)
        self.menu = []
        self.prev_y = 0
        self.x_pos = 0

    class Menu:
        def __init__(self, title_size, title="Menu", arrow="|"):
            self.title = title
            self.title_size = title_size
            self.titl_opt_dis = title_size + 8
            self.arrow = arrow
            self.x_arrow = 0
            self.options = []
            self.selected_index = 0
            self.scroll_offset = 0
            self.max_visible = 4
            self.opt_dis = 10
            self.target_y = self.titl_opt_dis
            self.current_y = self.titl_opt_dis

        def add_options(self, *options):
            self.options = list(options)
            self.selected_index = 0
            self.scroll_offset = 0
            self.target_y = self.titl_opt_dis
            self.current_y = self.titl_opt_dis

        def update_arrow(self, rot_turn):
            if not self.options:
                return
            if rot_turn == 1:
                self.selected_index = min(len(self.options) - 1, self.selected_index + 1)
            elif rot_turn == 2:
                self.selected_index = max(0, self.selected_index - 1)
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
            elif self.selected_index >= self.scroll_offset + self.max_visible:
                self.scroll_offset = self.selected_index - self.max_visible + 1
            relative_pos = self.selected_index - self.scroll_offset
            self.target_y = self.titl_opt_dis + (relative_pos * self.opt_dis)

    def show_menu(self, menu_obj, rot_turn):
        diff = menu_obj.target_y - menu_obj.current_y
        if abs(diff) > 0.1:
            menu_obj.current_y += diff * 0.3
        else:
            menu_obj.current_y = menu_obj.target_y

        self.oled.fill(0)
        self.center_text(menu_obj.title, 0)
        self.oled.hline(0, menu_obj.title_size + 2, self.width, 1)

        start = menu_obj.scroll_offset
        end = min(start + menu_obj.max_visible, len(menu_obj.options))
        for i in range(start, end):
            display_y = menu_obj.titl_opt_dis + ((i - start) * menu_obj.opt_dis)
            self.oled.text(menu_obj.options[i], 12, display_y, 1)

        self.oled.text(menu_obj.arrow, menu_obj.x_arrow, int(menu_obj.current_y), 1)

        if 'POWER' in globals():
            for row_i, row in enumerate(POWER):
                for col_i, c in enumerate(row):
                    self.oled.pixel(col_i + 110, row_i + 2, c)

        self.oled.show()

    def enter_option(self):
        self.oled.fill(0)
        print(self.menu.selected_index)

    def center_text(self, text, y):
        char_width = 8
        text_width = len(text) * char_width
        x = (self.width - text_width) // 2
        x = max(0, x)
        self.oled.text(text, x, y, 1)

    def hr_animation(self, y_buffer, bpm, beat):
        buffer_len = len(y_buffer)
        if buffer_len == 0:
            return

        # 1. Scroll the existing graph to the left by the size of the buffer
        self.oled.scroll(-buffer_len, 0)
        
        # 2. Clear the new space on the right side (only the graph area, Y: 11 to 54)
        self.oled.fill_rect(128 - buffer_len, 11, buffer_len, 44, 0)

        # 3. Draw the new line segments on the far right edge
        start_x = 128 - buffer_len
        for i, y in enumerate(y_buffer):
            current_x = start_x + i
            prev_y = self.prev_y if i == 0 else y_buffer[i - 1]
            
            # Connect the previous point to the current point
            self.oled.line(current_x - 1, prev_y, current_x, y, 1)

        # 4. Save the very last Y value for the next time this function is called
        self.prev_y = y_buffer[-1]

        # 5. Clear UI zones and redraw (this cleans up the UI text that got smeared by the scroll)
        self.oled.fill_rect(0, 0, 128, 11, 0)
        self.oled.fill_rect(0, 55, 128, 10, 0)
        self.center_text("[X] STOP", 55)
        
        if bpm is not None:
            self.oled.text("%d bpm" % bpm, 12, 0)
            
        if beat:
            for row_i, row in enumerate(HEART):
                for col_i, c in enumerate(row):
                    self.oled.pixel(col_i, row_i, c)
                    
        # 6. Push everything to the physical screen
        self.oled.show()

    def hrv_display(self, ppi, bpm, rmssd, sdnn):
        self.oled.fill(0)
        results_titl = ["MEAN HR:", "MEAN PPI:", "RMSSD:", "SDNN:"]
        results_num = [bpm, ppi, rmssd, sdnn]
        y = 0
        for result, num in zip(results_titl, results_num):
            x = 8
            self.oled.text(result, x, y, 1)
            x = (len(result) * 8) + 8
            self.oled.text(str(num), x, y)
            y += 16
        self.oled.show()

    def intro_anim(self, push_fifo=None):
        with open('intro.py', 'r') as f:
            exec(f.read())
            
        for row_i, row in enumerate(LOGOSTART):
            if rot.push_fifo.has_data() != True:
                for col_i, c in enumerate(row):
                        self.oled.pixel(col_i + 51, row_i + 10, c)
                self.oled.show()
            else:
                self.oled.fill(0)
        
        while push_fifo and (push_fifo.has_data() != True):
            for i in range(len(HEARTS)):
                if rot.push_fifo.has_data() != True:
                    for row_i, row in enumerate(HEARTS[i]):
                        for col_i, c in enumerate(row):
                            self.oled.pixel(col_i, row_i, c)
                    self.oled.show()
                    time.sleep(INTRODELAY)

        return False

    def state_3a_anim(self):
        self.oled.fill(0)
        ins = ["1. PLACE FINGER", "2. HOLD STILL", "STARTING IN"]
        self.center_text(ins[0], 8)
        self.center_text(ins[1], 16)
        self.center_text(ins[2], 24)
        self.center_text("3", 40)
        self.oled.show()

        for x_pos in [108, 114, 120]:
            self.oled.text(".", x_pos, 24, 1)
            self.oled.show()
            time.sleep(0.3)

        timer = 3
        count = 2

        for i in range(timer):
            self.oled.fill_rect(108, 24, 20, 8, 0)
            self.oled.fill_rect(60, 40, 8, 8, 0)
            for x_pos in [108, 114, 120]:
                self.oled.text(".", x_pos, 24, 1)
                self.oled.show()
                time.sleep(0.1)
            self.center_text(str(count), 40)
            self.oled.show()
            time.sleep(0.7)
            count -= 1

        self.oled.fill(0)
        self.center_text("RECORDING...", 28)
        self.oled.show()
        time.sleep(0.2)
        self.oled.fill(0)

    def quit(self):
        self.oled.fill(0)
        self.oled.show()
        raise SystemExit



class History:
    def __init__(self, oled):
        self.timestamp_options = []
        # variable to upload history filtered by client
        self.selected_history_list = []
        self.history_menu = oled.Menu(16, "History", ">")
        self.option = 0
        self.localdata = []

    def history_data(self, data):
        self.selected_history_list = data
    
    def make_options(self):
        for log in self.selected_history_list:
            #time = log.get("Time", "N/A")
            time = log
            if time != "N/A":
                self.timestamp_options.append(time)
        return self.timestamp_options
        
    def show_history(self, rot, oled):
        if self.timestamp_options:
            self.history_menu.add_options(*self.timestamp_options)
            while True:
                while rot.rot_fifo.has_data():
                    rot_turn = rot.rot_fifo.get()
                    self.history_menu.update_arrow(rot_turn)

                oled.show_menu(self.history_menu, self.option)

                if rot.push_fifo.has_data():
                    self.option = self.history_menu.selected_index
                    print("HISTORY INDEX", self.history_menu.selected_index)
                    #TODO
                    pass
    def local_file(self):        
        try:
            with open('localhistory.json') as f:
                self.localdata = json.load(f)
                print("local history successfully loaded")
        except:
            with open('localhistory.json', 'w') as f:
                pass
                print("local history file missing, created it")
                
    def local_add(self, client, reading):
        self.localdata.setdefault(client, []).append(reading) #setdefault creates an empty list if the user isn't in history, to prevent errors
        
    def local_load(self, client):
        self.data = self.localdata[client]
        return self.data

                



class App:
    def __init__(self, delay_time, oled, data, rot, kubios, mqtt, history, wifi_manager, accept_btn, remove_btn):
        self.delay = delay_time
        self.oled = oled
        self.data = data
        self.rot = rot
        self.accept_btn = accept_btn
        self.remove_btn = remove_btn
        self.kubios = kubios
        self.mqtt = mqtt
        self.history = history
        self.option = 0
        self.rot_change = None
        self.btn_val = False
        self.state = 0
        self.menu_item = oled.Menu(16, "Options", ">")
        self.wifi_manager = wifi_manager

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

    def state_menu(self):
        while self.rot.rot_fifo.has_data():
            rot_turn = self.rot.rot_fifo.get()
            self.menu_item.update_arrow(rot_turn)

        self.oled.show_menu(self.menu_item, 0)

        if self.check_btn_press():
            print("BUTTON PRESSED", self.check_btn_press())
            self.option = self.menu_item.selected_index
            print("INDEX", self.menu_item.selected_index)
            self.change_option_state()
            print("STATE", self.state)
            self.state_off()
            print("Selected:", self.option)

    def state_off(self):
        self.oled.oled.fill(0)
        self.oled.oled.show()

    def anim_state(self):
        interrupted = self.oled.intro_anim(push_fifo=self.rot.push_fifo)
        if interrupted:
            self.btn_val = False
            self.state = 2

    def change_option_state(self):
        if self.option == 0:
            self.state = 3
        elif self.option == 1:
            self.state = 5
        elif self.option == 2:
            self.state = 6
        elif self.option == 3:
            self.state = 7
        elif self.option == 4:
            self.state = 7
        elif self.option == 5:
            self.state = 8

    def state_3a(self):
        self.oled.state_3a_anim()
        self.state = 4

    def state_3b(self):
        self.data.read()
        while not self.check_btn_press():
            self.data.run(self.oled)
        self.data.read_off()
        self.btn_val = False

    def state_4(self):
        if self.data.count_sample < self.data.HRV_TIMER:
            self.oled.state_3a_anim()
        self.data.read()
        while self.data.count_sample < self.data.HRV_TIMER:
            print("SAMPLE", self.data.count_sample)
            self.data.run(self.oled)
            if self.check_btn_press():
                self.data.read_off()
                self.state = 2
                self.btn_val = False
                return
        self.data.read_off()
        self.data.hrv_mode(self.oled)

    def kubios_state(self):
        self.wifi_manager.wifi_ana()
        self.wifi_manager.wifi_on()

        mac = self.wifi_manager.get_pico_mac()
        self.kubios.mqtt_client(mac)
        print("CLIENT", self.kubios.client)
        self.kubios.connect_and_subscribe()

        if self.data.count_sample < self.data.HRV_TIMER:
            self.oled.state_3a_anim()
        self.data.read()
        while self.data.count_sample < self.data.HRV_TIMER:
            print("SAMPLE", self.data.count_sample)
            self.data.run(self.oled)
            if self.check_btn_press():
                self.data.read_off()
                self.state = 2
                self.btn_val = False
                return
        self.data.read_off()

        ppi_list = self.data.clean_ppi_list()
        print("PPILIST", ppi_list)
        if ppi_list:
            self.kubios.send_request(mac, ppi_list)
            response = self.kubios.wait_for_response()
            if response:
                print(response.get("data", {}).get("analysis", {}))
                self.kubios.show_responce(self.oled)
                while not self.rot.push_fifo.has_data():
                    pass
                self.rot.push_fifo.get()
        self.state = 2 
        

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


test_timestamps = [
    "23-01-15 08:30",  # Standard morning time
    "23-02-28 14:45",  # End of standard February
    "23-04-01 00:00",  # Just past midnight
    "23-07-04 12:00",  # Exactly noon
    "23-10-31 23:59",  # Last second of the day
    "24-02-29 10:15",  # Leap year day
    "22-12-25 07:05",  # Single-digit minutes/seconds
    "21-09-11 09:41",  # Zeroes in seconds
    "25-05-05 16:20",  # Afternoon time
    "20-01-01 01:01",  # All single digits (1s)
    "19-06-15 18:30",  # Standard evening time
    "18-08-08 08:08",  # Repeated digits
    "26-11-11 11:11",  # Repeated double digits
    "26-05-05 19:10",  # Current time example
    "99-12-31 23:59"   # End of century edge case
]

accept_btn = Btn(7)
remove_btn = Btn(9) 

mqtt = 0


wifi_manager = Wifi()
kubios = Kubios()

av = HR_sensor(250, 27)
data = Data(av)
OPTIONS = ("Measure HR", "Basic HRV", "Coffee", "Kubios", "History", "Shutdown")

rot = Rotary_encoder(30, 10, 11, 12)
oled = OLED(128, 64)

history = History(oled)
app = App(0.05, oled, data, rot, kubios, mqtt, history, wifi_manager, accept_btn, remove_btn)
app.menu_item.add_options(*OPTIONS)
app.oled.show_menu(app.menu_item, 0)
# USER INPUT
#app.state = 404
# HISTORY
#app.state = 67
while True:
    if app.state == 67:
        app.history.history_data(test_timestamps)
        app.history.make_options()
        app.history.show_history(app.rot, app.oled)
        app.history
    #if app.state == 404:
        #print("here")
        #app.history.enter_name(app.rot, app.accept_btn, app.remove_btn, app.oled)
    if app.state == 0:
        app.state_off()
        app.btn_val = False
        app.state = 1
    if app.state == 1:
        #app.anim_state()
        #if app.check_btn_press():
            #app.btn_val = False
            app.state = 2
    elif app.state == 2:
        while True:
            app.state_menu()
            if app.btn_val:
                app.btn_val = False
                break
        app.data.reset()
    elif app.state == 3:
        app.state_3a()
    elif app.state == 4:
        app.state_3b()
        app.state = 2
    elif app.state == 5:
        app.state_4()
        if app.check_btn_press():
            client = "Ana"
            history = app.data.hrv_history()
            app.history.local_file()
            app.history.local_add(client, history)
            app.history.local_load(client)

            print("HISTORY", history)
            app.state_off()
            app.state = 2
            app.btn_val = False
    elif app.state == 7:
        app.kubios_state()
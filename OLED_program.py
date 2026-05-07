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

class MQTT:
    def __init__():
        self.patient = ""
        self.patient_id = 0
        self.mac = 0
    


# ---------------------------------------------------------------------------
# Kubios — MQTT-based cloud HRV analysis
# ---------------------------------------------------------------------------

class Kubios:
    """
    Sends PPI (Peak-to-Peak Interval) data to the Kubios HRV cloud service
    via MQTT and retrieves the analysis result.
 
    Flow:
      1. mqtt_client()           create and configure the MQTT client
      2. connect_and_subscribe() open the connection and subscribe to responses
      3. send_request()          publish the PPI payload
      4. wait_for_response()     poll until the response arrives or times out
      5. show_responce()         render the key metrics on the OLED
    """

    # MQTT broker connection settings
    BROKER_IP = "194.110.232.94"
    BROKER_PORT = 1883
    REQUEST_TOPIC = b"kubios/request"
    RESPONSE_TOPIC = b"kubios/response"
    OUTPUT_FILE = "kubios_response.json"
    TIMEOUT_MS = 15000
    
    def __init__(self):
        self.client = None          # MQTTClient instance
        self.latest_response = None # Stores the most recent parsed JSON response
        
    def mqtt_client(self, mac):
        # Initialize the MQTT client with device MAC address as a client ID
        self.client = MQTTClient(
            client_id=(mac + "_ext").encode(),
            server=self.BROKER_IP, 
            port=self.BROKER_PORT)
        self.client.set_callback(self.mqtt_callback)

    def mqtt_callback(self, topic, msg):
        # Ignore messages from topics other than the response topic
        if topic != self.RESPONSE_TOPIC:
            return
        try:
            # Parse the incoming JSON message and store it
            self.latest_response = json.loads(msg)
        except ValueError:      
            self.latest_response = None

    def connect_and_subscribe(self):
        # Connect to the MQTT broker and subscribe to the response topic
        self.client.connect()
        self.client.subscribe(self.RESPONSE_TOPIC)

    def send_request(self, mac, ppi_list):
        # Build and publish the HRV analysis request payload
        payload = self.build_request_payload(mac, ppi_list)
        self.client.publish(self.REQUEST_TOPIC, json.dumps(payload))

    def wait_for_response(self):
        '''
        Wait for incoming messages until a response arrives or the timeout is over
        Side-effects:
          - Saves the response to OUTPUT_FILE.
          - Disconnects the MQTT client when done.

        Returns:
            dict | None: The parsed Kubios response, or None on timeout.
        '''
        start = time.ticks_ms()

        while time.ticks_diff(time.ticks_ms(), start) < self.TIMEOUT_MS:
            self.client.check_msg()
            
            if self.latest_response:
                print("Response received:")
                self.save_json_to_pico(self.OUTPUT_FILE, self.latest_response)
                break
            time.sleep_ms(200)  # Short delay to avoid busy-waiting

        self.client.disconnect()
        print("Client disconnected")
        return self.latest_response

    def build_request_payload(self, mac_address, ppi_list):
        '''
        Construct the JSON payload for a readiness analysis request using RRI (PPI) data

        Returns:
        dict: Payload with type 'RRI' and readiness analysis request.
        '''
        if ppi_list:
            return {
                "mac": mac_address,
                "type": "RRI",
                "data": ppi_list,
                "analysis": {"type": "readiness"}
            }

    def show_responce(self, oled):
        '''
        Display Kubios HRV analysis results on the OLED screen
        Metrics shown: BPM, PPI, RMSSD, SDNN, SNS index, PNS index.
        '''
        if not self.latest_response:
            oled.oled.fill(0)
            oled.center_text("No response", 28)
            oled.oled.show()
            return

        print("RESPONCE", self.latest_response)

        # Extract and round HRV metrics from the nested response structure
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

        # Render all metrics on the OLED display (128x64, 8px per row)
        oled.oled.fill(0)
        oled.oled.text("HR:"    + str(bpm),   0,  0, 1)
        oled.oled.text("PPI:"   + str(ppi),   0, 10, 1)
        oled.oled.text("RMSSD:" + str(rmssd), 0, 20, 1)
        oled.oled.text("SDNN:"  + str(sdnn),  0, 30, 1)
        oled.oled.text("SNS:"   + str(sns),   0, 42, 1)
        oled.oled.text("PNS:"   + str(pns),   0, 52, 1)
        oled.oled.show()



    def save_json_to_pico(self, filename, data):
        # Serialize and write the response JSON to a file on the Pico filesystem
        with open(filename, "w") as file:
            json.dump(data, file)


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


# ---------------------------------------------------------------------------
# Data — signal processing, beat detection, and HRV calculation
# ---------------------------------------------------------------------------

class Data():
    '''
    Core signal processing class for the PPG heart-rate sensor.
 
    Responsibilities:
      - Moving-average smoothing of the raw ADC signal
      - Adaptive threshold-based beat detection
      - PPI calculation and artifact rejection
      - BPM calculation
      - HRV metrics: RMSSD and SDNN
      - Normalised waveform for the OLED oscilloscope display
    '''

    HRV_TIMER = 7500    # Number of samples required before HRV analysis (~30 s at 250 Hz)

    def __init__(self, hr_sensor, sampling_rate=250):
        '''
        Args:
            hr_sensor    : HR_sensor (Fifo) instance that gives ADC samples.
            sampling_rate: ADC sampling frequency in Hz (default 250).
        '''
        self.av = hr_sensor
        self.sampling_rate = sampling_rate

        # --- Signal history ------------------------------------------------
        self.history = []
        self.MAX_HISTORY = 500

        # --- Current sample state ------------------------------------------
        self.sample = 0
        self.count_sample = 0
        self.max_sample = 0
        self.min_sample = 0

        # --- Beat-detection thresholds -------------------------------------
        self.threshold_on = 0
        self.threshold_off = 0

        # --- Beat tracking -------------------------------------------------
        self.beats = []
        self.MAX_BEATS = 20
        self.beat = False
        self.MIN_BEAT_INTERVAL = 400
        self.MAX_BEAT_INTERVAL = 2000
        self.last_beat_time = 0

        # --- BPM / PPI metrics --------------------------------------------
        self.avg_ppi_interval = 0
        self.bpm = None
        self.bpm_list = []
        self.mean_bpm = 0
        self.mean_ppi = 0
        self.ppi_list = []

        # --- HRV metrics --------------------------------------------------
        self.RMMDS = 0
        self.SDNN = 0
        
        # --- Display helpers ----------------------------------------------
        self.last_y = 0
        self.y_buffer = []

        # --- Smoothing ----------------------------------------------------
        self.smooth_buf = []
        self.SMOOTH_WINDOW = 30

        self.led = Led(22, mode=Pin.OUT, brightness=1)  # Beat indicator LED
        
        
    # ------------------------------------------------------------------
    # Timer control
    # ------------------------------------------------------------------

    def read(self):
        '''Start the Piotimer to trigger HR_sensor.handler at the set sample rate.'''
        self.tmr = Piotimer(mode=Piotimer.PERIODIC, freq=self.sampling_rate, callback=self.av.handler)

    def read_off(self):
        '''Stop the timer and flush any remaining samples from the FIFO.'''
        while self.av.has_data():
            self.av.get()
        self.tmr.deinit()

    # ------------------------------------------------------------------
    # Data export
    # ------------------------------------------------------------------
 
    def get_data(self):
        '''
        Return the current HRV DATA as a dictionary for local storage.
 
        Returns:
            dict with keys: Time, Mean PPI, Mean BPM, RMMDS, SDNN.
        '''

        t = time.localtime()
        timestamp = "{:02d}-{:02d}-{:02d} {:02d}:{:02d}".format(t[0] % 100, t[1], t[2], t[3], t[4])
        return {
            "Time": timestamp,
            "Mean PPI": self.mean_ppi,
            "Mean BPM": self.mean_bpm,
            "RMMDS": self.RMMDS,
            "SDNN": self.SDNN
        }

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def if_full(self, l, max_l):
        '''Drop the oldest element from list l when it exceeds max_l items.'''
        if len(l) > max_l:
            l.pop(0)

    # ------------------------------------------------------------------
    # HRV analysis entry points
    # ------------------------------------------------------------------

    def hrv_mode(self, oled):
        '''        
        Run artifact filtering and HRV calculations, then update the display.
        Called once after the 30-second recording window is complete.
        '''
        self.median_filter()
        self.calc_rmmds()
        self.calc_sdnn()
        oled.hrv_display(self.mean_ppi, self.mean_bpm, self.RMMDS, self.SDNN)

    def hrv_history(self):
        '''Return the current HRV snapshot (delegates to get_data).'''
        hrv_history = self.get_data()
        return hrv_history


    # ------------------------------------------------------------------
    # Main processing loop (called repeatedly from App states)
    # ------------------------------------------------------------------

    def run(self, oled):
        '''
        Process up to 250 buffered ADC samples in one call.
 
        For each sample:
          1. Apply moving-average smoothing.
          2. Update the adaptive min/max and thresholds every 50 samples.
          3. Detect beat rising edge above threshold_on.
          4. Calculate PPI and BPM on each new beat.
          5. Detect beat falling below threshold_off.
          6. Update the OLED waveform at 1/10 of the sample rate.

        '''

        for _ in range(250):
            if self.av.has_data():
                self.sample = self.av.get()
                self.count_sample += 1
                self.sample = self.smooth()         # Low-pass filter
                self.history.append(self.sample)
                self.if_full(self.history, self.MAX_HISTORY)
                
                # Recalculate the adaptive thresholds every 50 samples
                if self.count_sample % 50 == 0 and len(self.history) > 100:
                    self.max_sample = max(self.history)
                    self.min_sample = min(self.history)
                    amplitude = self.max_sample - self.min_sample
                    # Threshold ON  = 75 % of the amplitude above the minimum
                    self.threshold_on = self.min_sample + int(amplitude * 0.75)
                    # Threshold OFF = midpoint of the range
                    self.threshold_off = (self.min_sample + self.max_sample) // 2

                # --- Beat rising edge detection ---
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

                # --- Beat falling edge detection ---
                if self.sample < self.threshold_off and self.beat:
                    self.beat = False
                    self.led.off()

                # Normalise Y for the oscilloscope display
                self.refresh()

                # Feed the OLED waveform at ~25 Hz (every 10 samples at 250 Hz)
                if self.count_sample % 10 == 0:
                    self.y_buffer.append(self.last_y)
                    oled.hr_animation(self.y_buffer, self.bpm, self.beat)
                    self.y_buffer.clear()


    # ------------------------------------------------------------------
    # Artifact rejection
    # ------------------------------------------------------------------

    def median_filter(self, max_change_percent=0.2, window_size=5):
        '''
        Remove outlier PPI values using a two-pass median-based filter.
 
        Pass 1  find the global median; accept the first value within
                max_change_percent of it as the seed for the clean list.
        Pass 2  for each subsequent value, compare it to the local median
                of the last window_size accepted values; discard if it
                deviates by more than max_change_percent.
 
        Args:
            max_change_percent: Maximum fractional deviation allowed (default 20 %).
            window_size       : Number of recent values used for local baseline.
 
        Returns:
            list: Cleaned PPI list (also stored in self.ppi_list).
        '''

        if not self.ppi_list or len(self.ppi_list) < 2:
            return self.ppi_list

        sorted_ppis = sorted(self.ppi_list)
        global_median = sorted_ppis[len(sorted_ppis) // 2]

        clean_list = []
        start_idx = 0

        # Seed the clean list with the first value close to the global median
        for i in range(len(self.ppi_list)):
            if abs(self.ppi_list[i] - global_median) / global_median <= max_change_percent:
                clean_list.append(self.ppi_list[i])
                start_idx = i + 1
                break

        if not clean_list:
            clean_list = [global_median]
            start_idx = 0

        # Accept or reject each subsequent value based on the rolling local median
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

    # ------------------------------------------------------------------
    # Beat metrics
    # ------------------------------------------------------------------

    def calculate_ppi(self):
        if len(self.beats) < 3:
            return
        diff = time.ticks_diff(self.beats[-1], self.beats[-2])
        #print("DIFF ppi", diff)
        if self.MIN_BEAT_INTERVAL < diff < self.MAX_BEAT_INTERVAL:
            self.ppi_list.append(diff)
            self.if_full(self.ppi_list, 30)
            print("ppi_List", self.ppi_list)
            self.mean_ppi = sum(self.ppi_list) / len(self.ppi_list)


    def calculate_bpm(self):
        if self.mean_ppi > 0:
            self.bpm = int(60000 / self.ppi_list[-1])
            self.mean_bpm = int(60000 / self.mean_ppi)

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


    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def refresh(self):
        ''' 
        Map the current smoothed sample to a Y pixel coordinate.
        Normalises the sample into the range [0, 50] relative to the
        dynamic min/max and stores it in self.last_y for the waveform.
        '''
        if self.max_sample - self.min_sample > 0:
            self.last_y = 50 - int(
                32 * (self.sample - self.min_sample) / (self.max_sample - self.min_sample)
            )

    def smooth(self):
        ''' Simple moving-average (box filter) to the raw ADC sample.'''
        self.smooth_buf.append(self.sample)
        if len(self.smooth_buf) > self.SMOOTH_WINDOW:
            self.smooth_buf.pop(0)
        return sum(self.smooth_buf) // len(self.smooth_buf)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def reset(self):
        '''Reset all signal processing state to prepare for a new recording session.'''
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
        '''
        IRQ handler for encoder rotation 
 
          B = 1 → clockwise      → push 1
          B = 0 → counter-clockwise → push 2
        '''

        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_rot_time) > 150:
            if self.b.value():
                self.rot_fifo.put(1)
            else:
                self.rot_fifo.put(2)
                print("handler2")
            self.last_rot_time = now

    def handler_push(self, pin):
        '''
        IRQ handler for the push button
 
        Pushes 0 onto push_fifo after a 350 ms debounce window.
        '''

        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_push_time) > 350:
            self.push_fifo.put(0)
            print("done")
            self.last_push_time = now

        
# ---------------------------------------------------------------------------
# OLED — display driver and UI components
# ---------------------------------------------------------------------------

class OLED:
    '''
    Wrapper around the SSD1306 I2C driver that provides:
       A scrollable Menu widget
       A real-time HR waveform animation
       An HRV results screen
       An intro animation
    '''

    def __init__(self, width, height):
        '''
        Args:
            width : Display width in pixels (128).
            height: Display height in pixels (64).
        '''

        self.width = width
        self.height = height
        self.i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=1000000)
        self.oled = SSD1306_I2C(self.width, self.height, self.i2c)
        self.menu = []
        self.prev_y = 0
        self.x_pos = 0


    # ------------------------------------------------------------------
    # Inner class: Menu
    # ------------------------------------------------------------------

    class Menu:
        '''
        A scrollable list menu that renders on the OLED.
 
        Features:
           Animated arrow that glides to the highlighted option
           Auto-scrolling when the selection goes off-screen
       '''

        def __init__(self, title_size, title="Menu", arrow=">"):
            '''
            Args:
                title_size: Y offset in pixels that the title occupies.
                title     : Menu heading string.
                arrow     : Character used as the selection cursor.
            '''

            self.title = title
            self.title_size = title_size
            self.titl_opt_dis = title_size + 8  # Y position of the first option
            self.arrow = arrow
            self.x_arrow = 0
            self.options = []
            self.selected_index = 0
            self.scroll_offset = 0
            self.max_visible = 4                # Maximum options shown at once
            self.opt_dis = 10                   # Pixel spacing between options
            self.target_y = self.titl_opt_dis
            self.current_y = self.titl_opt_dis

        def add_options(self, *options):
            '''Replace the current option list and reset selection state.'''
            self.options = list(options)
            self.selected_index = 0
            self.scroll_offset = 0
            self.target_y = self.titl_opt_dis
            self.current_y = self.titl_opt_dis

        def update_arrow(self, rot_turn):
            '''
            Move the selection up or down by one step.
 
            Scrolls the visible window when the cursor reaches the edge.
 
            Args:
                rot_turn: 1 = move down, 2 = move up.
            '''

            if not self.options:
                return
            if rot_turn == 1:
                self.selected_index = min(len(self.options) - 1, self.selected_index + 1)
            elif rot_turn == 2:
                self.selected_index = max(0, self.selected_index - 1)

            # Adjust the scroll window to keep the selection visible
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
            elif self.selected_index >= self.scroll_offset + self.max_visible:
                self.scroll_offset = self.selected_index - self.max_visible + 1
            
            # Adjust the scroll window to keep the selection visible
            relative_pos = self.selected_index - self.scroll_offset
            self.target_y = self.titl_opt_dis + (relative_pos * self.opt_dis)


    # ------------------------------------------------------------------
    # Menu rendering
    # ------------------------------------------------------------------

    def show_menu(self, menu_obj):
        '''
        Render one frame of the menu with an eased arrow animation.
 
        The arrow moves 30 % of the remaining distance per frame.
 
        Args:
            menu_obj: Menu instance to render.
            rot_turn: Unused here (arrow position updated externally via update_arrow).
        '''
        # Move the arrow toward its target
        diff = menu_obj.target_y - menu_obj.current_y
        if abs(diff) > 0.1:
            menu_obj.current_y += diff * 0.3
        else:
            menu_obj.current_y = menu_obj.target_y

        self.oled.fill(0)
        self.center_text(menu_obj.title, 0)
        self.oled.hline(0, menu_obj.title_size + 2, self.width, 1)

        # Draw only the visible slice of the options list
        start = menu_obj.scroll_offset
        end = min(start + menu_obj.max_visible, len(menu_obj.options))
        for i in range(start, end):
            display_y = menu_obj.titl_opt_dis + ((i - start) * menu_obj.opt_dis)
            self.oled.text(menu_obj.options[i], 12, display_y, 1)

        # Draw the selection arrow at the interpolated Y position
        self.oled.text(menu_obj.arrow, menu_obj.x_arrow, int(menu_obj.current_y), 1)

        # Draw the power icon in the top-right corner
        if 'POWER' in globals():
            for row_i, row in enumerate(POWER):
                for col_i, c in enumerate(row):
                    self.oled.pixel(col_i + 110, row_i + 2, c)

        self.oled.show()

    def enter_option(self):
        '''Clear the screen when the user confirms a menu selection'''
        self.oled.fill(0)
        print(self.menu.selected_index)

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------


    def center_text(self, text, y):
        ''' Draw text horizontally centred on the display.'''
        char_width = 8
        text_width = len(text) * char_width
        x = (self.width - text_width) // 2
        x = max(0, x)
        self.oled.text(text, x, y, 1)

    
    # ------------------------------------------------------------------
    # Animations and transitions
    # ------------------------------------------------------------------

    def hr_animation(self, y_buffer, bpm, beat):
        '''
        Scroll the live PPG waveform left and append new samples on the right.
 
        Algorithm:
          1. hardware-scroll the frame buffer left by len(y_buffer) pixels
          2. clear the newly exposed right strip (graph area Y: 11-54)
          3. draw line segments connecting each new sample to the previous
          4. clear and redraw the UI zones (top bar, bottom bar)
          5. push the frame to the display
 
        Args:
            y_buffer: List of normalised Y values (from Data.refresh).
            bpm     : Current BPM to display; None if not yet calculated.
            beat    : True while a beat is active 
        '''

        buffer_len = len(y_buffer)
        if buffer_len == 0:
            return

        # Scroll the existing graph to the left by the size of the buffer
        self.oled.scroll(-buffer_len, 0)
        
        # Clear the new space on the right side (only the graph area, Y: 11 to 54)
        self.oled.fill_rect(128 - buffer_len, 11, buffer_len, 44, 0)

        # Draw the new line segments on the far right edge
        start_x = 128 - buffer_len
        for i, y in enumerate(y_buffer):
            current_x = start_x + i
            prev_y = self.prev_y if i == 0 else y_buffer[i - 1]
            
            # Connect the previous point to the current point
            self.oled.line(current_x - 1, prev_y, current_x, y, 1)

        # Save the very last Y value for the next time this function is called
        self.prev_y = y_buffer[-1]

        # Clear UI zones and redraw (this cleans up the UI text that got smeared by the scroll)
        self.oled.fill_rect(0, 0, 128, 11, 0)
        self.oled.fill_rect(0, 55, 128, 10, 0)
        self.center_text("[X] STOP", 55)
        
        if bpm is not None:
            self.oled.text("%d bpm" % bpm, 12, 0)
            
        if beat:
            # Draw the COFFEE bitmap at the top-left corner
            for row_i, row in enumerate(HEART):
                for col_i, c in enumerate(row):
                    self.oled.pixel(col_i, row_i, c)
                    
        # Push everything to the physical screen
        self.oled.show()

    def hrv_display(self, ppi, bpm, rmssd, sdnn):
        '''
        Show a four-row HRV summary screen.
 
        Args:
            ppi  : Mean PPI in ms.
            bpm  : Mean HR in bpm.
            rmssd: RMSSD in ms.
            sdnn : SDNN in ms.
        '''

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
        ''' Play the startup logo animation. '''
        with open('intro.py', 'r') as f:
            exec(f.read())
        
        # Draw the static logo frame, pixel by pixel
        for row_i, row in enumerate(LOGOSTART):
            if rot.push_fifo.has_data() != True:
                for col_i, c in enumerate(row):
                        self.oled.pixel(col_i + 51, row_i + 10, c)
                self.oled.show()
            else:
                self.oled.fill(0)   # User skipped – clear screen

        # Cycle through the animation until the button is pressed
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
        '''
        Display the pre-measurement countdown animation.
 
        Shows instructions ("PLACE FINGER", "HOLD STILL") and counts down
        from 3 to 1, then shows "RECORDING..." before returning.
        '''
        self.oled.fill(0)
        ins = ["1. PLACE FINGER", "2. HOLD STILL", "STARTING IN"]
        self.center_text(ins[0], 8)
        self.center_text(ins[1], 16)
        self.center_text(ins[2], 24)
        self.center_text("3", 40)
        self.oled.show()

        # Animate three dots appearing after "STARTING IN"
        for x_pos in [108, 114, 120]:
            self.oled.text(".", x_pos, 24, 1)
            self.oled.show()
            time.sleep(0.3)

        # Count down 2 → 1 → 0
        timer = 3
        count = 2

        for i in range(timer):
            self.oled.fill_rect(108, 24, 20, 8, 0)  # Clear the dots
            self.oled.fill_rect(60, 40, 8, 8, 0)    # Clear the digit
            for x_pos in [108, 114, 120]:
                self.oled.text(".", x_pos, 24, 1)
                self.oled.show()
                time.sleep(0.1)
            self.center_text(str(count), 40)
            self.oled.show()
            time.sleep(0.7)
            count -= 1

        # Show "RECORDING..." briefly before the ADC timer starts
        self.oled.fill(0)
        self.center_text("RECORDING...", 28)
        self.oled.show()
        time.sleep(0.2)
        self.oled.fill(0)


# ---------------------------------------------------------------------------
# History — local flash storage for HRV session logs
# ---------------------------------------------------------------------------

class History:
    '''
    Manages per-user HRV session history stored as JSON on the Pico's flash.
 
    Data layout in localhistory.json:
      { "username": [ { HRV snapshot dict }, ... ], ... }
    '''

    FILENAME = 'localhistory.json'

    def __init__(self, oled):
        self.timestamp_options = []                     # Menu option labels (timestamps)
        self.selected_history_list = []                 # variable to upload history filtered by client
        self.history_menu = oled.Menu(16, "History", ">")
        self.option = 0
        self.localdata = {}
        self.local_file()   # Load existing data from flash at startup

    def history_data(self, data):
        '''Set the list of HRV records to display (call before show_history).'''
        self.selected_history_list = data
    
    def make_options(self):
        '''
        Build the menu option list from the current history records.
 
        Always inserts "Exit" as the first option (index 0).
        '''

        self.timestamp_options = ["Exit"]

        sorted_logs = sorted(
            self.selected_history_list,
            key=lambda log: log.get("Time", ""),
            reverse=True    # newest first
        )

        for log in sorted_logs:
            time = log.get("Time", "N/A")
            #time = log
            if time != "N/A":
                self.timestamp_options.append(time)
        return self.timestamp_options
        
    def show_history(self, rot, oled):
        '''
        Run the interactive history browser.
 
        The user scrolls through timestamps with the rotary encoder and
        pushes to view the details of a selected recording.  Pushing again
        while viewing a record returns to the browser.
 
        Args:
            rot : Rotary_encoder instance.
            oled: OLED instance.
        '''

        if self.timestamp_options:
            self.history_menu.add_options(*self.timestamp_options)
            while True:
                # Handle rotation to move the menu cursor
                while rot.rot_fifo.has_data():
                    rot_turn = rot.rot_fifo.get()
                    self.history_menu.update_arrow(rot_turn)

                oled.show_menu(self.history_menu)

                # Handle button press to select or exit
                if rot.push_fifo.has_data():
                    button_val = rot.push_fifo.get()
                    self.option = self.history_menu.selected_index
                    print("HISTORY INDEX", self.history_menu.selected_index)

                    if self.option == 0:
                        return 2        # "Exit" selected → back to main menu

                    # Display the selected recording's HRV metrics
                    selected_log = self.selected_history_list[self.option - 1]
                    print("Log Details:", selected_log)
                    ppi = selected_log.get('Mean PPI')
                    bpm = selected_log.get('Mean BPM')
                    rmssd = selected_log.get('RMMDS')
                    sdnn = selected_log.get('SDNN')

                    # Show the detail screen; any press returns to the list
                    while True:
                        oled.hrv_display(ppi, bpm, rmssd, sdnn)
                        if rot.push_fifo.has_data():
                            rot.push_fifo.get()
                            return 8


    # ------------------------------------------------------------------
    # Flash I/O
    # ------------------------------------------------------------------

    def local_file(self):  
        '''
        Load the history JSON file from flash into self.localdata.
 
        Creates an empty file if none exists or if the file is corrupted.
        '''
      
        try:
            with open(self.FILENAME, 'r') as f:
                self.localdata = json.load(f)
                print("local history successfully loaded")
        except(OSError, ValueError):
            self.localdata = {}
            self.save_to_disk()
            print("Local history initialized")
           
    def save_to_disk(self):
        '''Persist self.localdata to flash as JSON.'''
        with open(self.FILENAME, 'w') as f:
            json.dump(self.localdata, f)
                
    def local_add(self, client, reading):
        '''
        Append one HRV reading to the specified client's history and save.
 
        Args:
            client : Username string (used as the dictionary key).
            reading: HRV snapshot dict from Data.get_data().
        '''

        if client not in self.localdata:
            self.localdata[client] = []
        self.localdata[client].append(reading)
        self.save_to_disk()

    def local_load(self, client):
        '''
        Load and return the history list for a given client.
 
        Args:
            client: Username string.
 
        Returns:
            list: List of HRV snapshot dicts for that user.
        '''

        self.selected_history_list = self.localdata[client]
        return self.selected_history_list


# ---------------------------------------------------------------------------
# App — top-level state machine
# ---------------------------------------------------------------------------

class App:
    '''
    Application controller implementing a finite-state machine.
 
    Each state corresponds to a distinct screen or
    function of the device.
    '''
    
    def __init__(self, delay_time, oled, data, rot, kubios, mqtt, 
                history, wifi_manager, accept_btn, remove_btn):
        self.delay = delay_time
        self.oled = oled
        self.data = data
        self.rot = rot
        self.accept_btn = accept_btn
        self.remove_btn = remove_btn
        self.kubios = kubios
        self.mqtt = mqtt
        self.history = history
        self.option = 0          # Index of the last selected menu item
        self.rot_change = None
        self.btn_val = False     # Latched button state (True = pressed)
        self.state = 0           # Current application state
        self.menu_item = oled.Menu(16, "Options", ">")
        self.wifi_manager = wifi_manager
        self.coffe_ready = 0


    # ------------------------------------------------------------------
    # Input helpers
    # ------------------------------------------------------------------

    def check_btn_press(self):
        '''
        Toggle and return the latched button state.
 
        Returns:
            bool: Current latched button state.
        '''

        if self.rot.push_fifo.has_data():
            self.change = self.rot.push_fifo.get()
            if self.change == 0:
                if self.btn_val == 0:
                    self.btn_val = 1
                else:
                    self.btn_val = 0
            else:
                 # Discard any additional queued events
                while self.rot.push_fifo.has_data():
                    self.rot.push_fifo.get()
        return self.btn_val


    def change_option_state(self):
        '''Map the selected menu index to the next application state.'''
        state_map = {0: 3, 1: 5, 2: 6, 3: 7, 4: 8, 5: 9}
        self.state = state_map.get(self.option, self.state)

    # ------------------------------------------------------------------
    # State handlers
    # ------------------------------------------------------------------


    def state_off(self):
        '''Clear the OLED (used between state transitions).'''
        self.oled.oled.fill(0)
        self.oled.oled.show()


    def anim_state(self):
        '''
        State 1 handler. 
        Play the intro animation.
        '''
        interrupted = self.oled.intro_anim(push_fifo=self.rot.push_fifo)
        if interrupted:
            self.btn_val = False
            self.state = 2


    def state_menu(self):
        '''
        State 2 handler. 
        Render the main menu and handle selection.
        '''

        while self.rot.rot_fifo.has_data():
            rot_turn = self.rot.rot_fifo.get()
            self.menu_item.update_arrow(rot_turn)

        self.oled.show_menu(self.menu_item)

        if self.check_btn_press():
            print("BUTTON PRESSED", self.check_btn_press())
            self.option = self.menu_item.selected_index
            print("INDEX", self.menu_item.selected_index)
            self.change_option_state()  # Map option index → next state
            print("STATE", self.state)
            self.state_off()
            print("Selected:", self.option)

    def state_3a(self):
        '''
        State 3 handler.
        Show the pre-measurement countdown, then go to state 4.
        '''
        self.oled.state_3a_anim()
        self.state = 4


    def state_3b(self):
        '''
        State 4 handler. 
        Live HR measurement (free-running until button press).
 
        Starts the ADC timer, runs the signal processing loop, and stops
        when the user presses the button.
        '''
        self.data.read()
        while not self.check_btn_press():
            self.data.run(self.oled)
        self.data.read_off()
        self.btn_val = False


    def state_5(self):
        '''
        State 5 handler.
        HRV recording (fixed 30-second window).
 
        Records until HRV_TIMER samples are collected, then displays
        the HRV results.  The user can abort early by pressing the button.
        '''

        if self.data.count_sample < self.data.HRV_TIMER:
            print("SAMPLE", self.data.count_sample)
            self.oled.state_3a_anim()

        self.data.read()
        while self.data.count_sample < self.data.HRV_TIMER:
            self.data.run(self.oled)
            if self.check_btn_press():
                self.data.read_off()
                self.state = 2          # Abort → back to menu
                self.btn_val = False
                return
        self.data.read_off()
        self.data.hrv_mode(self.oled)   # Display RMSSD / SDNN / BPM / PPI

    def coffe_state(self):
        '''
        State 6 handler.
        Coffee Readiness Index.
 
        '''

        self.history.make_options()
        if len(self.history.timestamp_options) > 1:
            selected_log = self.selected_history_list[0]
            ppi = selected_log.get('Mean PPI')
            bpm = selected_log.get('Mean BPM')
            rmssd = selected_log.get('RMMDS')
            sdnn = selected_log.get('SDNN')
            coffee_idx = round(rmssd / sdnn * 10)
            if coffee_idx > 5:
                return True
            else:
                return False

    def state_7(self):
        '''
        State 7 handler.
        Kubios cloud HRV analysis.
 
        Steps:
          1. Connect to Wi-Fi
          2. Set up MQTT client
          3. Record 30 s of PPG data
          4. Clean the PPI list and send to Kubios
          5. Wait for and display the cloud response
          6. Return to menu
        '''

        self.wifi_manager.wifi_ana()
        self.wifi_manager.wifi_on()

        mac = self.wifi_manager.get_pico_mac()
        self.kubios.mqtt_client(mac)
        print("CLIENT", self.kubios.client)
        self.kubios.connect_and_subscribe()

        if self.data.count_sample < self.data.HRV_TIMER:
            self.oled.state_3a_anim()
        self.data.read()
        while self.data.count_sample < self.data.HRV_TIMER or len(self.data.ppi_list) < 20:
            print("PPI length", len(self.data.ppi_list))
            self.data.run(self.oled)
            print("SAMPLE", self.data.count_sample)
            if self.check_btn_press():
                self.data.read_off()
                self.state = 2
                self.btn_val = False
                return
        self.data.read_off()
        ppi_list = self.data.ppi_list
        #ppi_list = self.data.median_filter()
        print("PPILIST", ppi_list)
        if ppi_list:
            self.kubios.send_request(mac, ppi_list)
            response = self.kubios.wait_for_response()
            if response:
                #print(response.get("data", {}).get("analysis", {}))
                self.kubios.show_responce(self.oled)
                while not self.rot.push_fifo.has_data():
                    pass
                self.rot.push_fifo.get()
        self.state = 2 


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
# Hardware initialisation
# ---------------------------------------------------------------------------

accept_btn = Btn(7)
remove_btn = Btn(9) 

mqtt = 0
client = User_input()

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
app.oled.show_menu(app.menu_item)
# USER INPUT
#app.state = 404
# HISTORY
#app.state = 67


# ---------------------------------------------------------------------------
# Main state-machine loop
# ---------------------------------------------------------------------------

app.state = 0
client = "Ana"

while True:

    # --- Development state: history viewer with dummy data ---
    if app.state == 67:
        app.history.history_data(test_timestamps)
        app.history.make_options()
        app.history.show_history(app.rot, app.oled)
        app.history

    # --- Development state: name entry screen ---
    if app.state == 404:
        #print("here")
        client.enter_name(app.rot, app.accept_btn, app.remove_btn, app.oled)

    # State 0: power-off
    if app.state == 0:
        app.state_off()
        if app.check_btn_press():
            app.btn_val = False
            app.state = 1

    # State 1: intro animation
    if app.state == 1:
        app.anim_state()
        if app.check_btn_press():
            app.btn_val = False
            app.state = 2

    # State 2: main menu. Spin until a selection
    elif app.state == 2:
        while True:
            app.state_menu()
            if app.btn_val:
                app.btn_val = False
                break
        app.data.reset()    # Clear previous recording on every menu visit

    # State 3: countdown animation before live HR measurement
    elif app.state == 3:
        app.state_3a()
    
    # State 4: live HR measurement (free-running)
    elif app.state == 4:
        app.state_3b()
        app.state = 2

    # State 5: fixed-window HRV recording → save result to local history
    elif app.state == 5:
        app.state_5()
        if app.check_btn_press():
            history = app.data.hrv_history()
            print("HISTORY", history)
            app.history.local_file()
            app.history.local_add(client, history)
            app.history.local_load(client)

    
            app.state_off()
            app.state = 2
            app.btn_val = False
    
    # State 6: coffee readiness (not yet implemented)
    elif app.state == 6:
        if app.coffe_state() == True:
            oled.coffeegood()
        else:
            oled.coffeebad()
        if app.check_btn_press():
            app.btn_val = False
            app.state = 2
    
    # State 7: Kubios cloud HRV analysis
    elif app.state == 7:
        app.state_7()

    # State 8: local history browser
    elif app.state == 8:
        #TODO put it into a state
        app.history.local_file()
        app.history.local_load(client)
        app.history.make_options()
        app.state = app.history.show_history(app.rot, app.oled)
    
    # State 9: shutdown scree
    elif app.state == 9:
        app.state_off
        if app.check_btn_press():
            app.btn_val = False
            app.state = 1

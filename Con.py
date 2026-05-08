from umqtt.simple import MQTTClient  # Kubios + MQTT
import network                        # Wifi
import ubinascii                      # Wifi (MAC address)
import time                           # Kubios + Wifi + MQTT
import json                           # Kubios + MQTT
import gc


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
        self._bpm = 0
        self._ppi = 0
        self._rmssd = 0
        self._sdnn = 0
        self._sns =  0
        self._pns = 0
        self._time = 0
        
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
        gc.collect()
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

    def extract_result(self):
        '''
        Extract and round HRV metrics from the nested response structure
        '''
        if not self.latest_response:
            return 0
        else:
            result = self.latest_response.get("data", {}).get("analysis", {})
            bpm   = result.get("mean_hr_bpm", "N/A")
            self._bpm = str(round(float(bpm)))
            ppi   = result.get("mean_rr_ms",  "N/A")
            self._ppi = str(round(float(ppi)))
            rmssd = result.get("rmssd_ms",    "N/A")
            self._rmssd = str(round(float(rmssd)))
            sdnn  = result.get("sdnn_ms",     "N/A")
            self._sdnn = str(round(float(sdnn)))
            sns   = result.get("sns_index",   "N/A")
            self._sns = str(round(float(sns), 3))
            pns   = result.get("pns_index",   "N/A")
            self._pns = str(round(float(pns), 3))
            timestamp_str = result.get("create_timestamp",   "N/A")

            # Create a Unix Timestamp
            if timestamp_str != "N/A":
                date_part, time_part = timestamp_str.split("T")
                year, mm, dd = [int(x) for x in date_part.split("-")]
                time_clean = time_part.split("+")[0].split("-")[0].split(".")[0]
                hh, mins, secs = [int(x) for x in time_clean.split(":")]
                self._time = time.mktime((year, mm, dd, hh, mins, secs, 0, 0))
            return 1

    def show_responce(self, oled):
        '''
        Display Kubios HRV analysis results on the OLED screen
        Metrics shown: BPM, PPI, RMSSD, SDNN, SNS index, PNS index.
        '''

        self.extract_result()

        # Render all metrics on the OLED display (128x64, 8px per row)
        oled.oled.fill(0)
        oled.oled.text("HR:"    + str(self._bpm),   0,  0, 1)
        oled.oled.text("PPI:"   + str(self._ppi),   0, 10, 1)
        oled.oled.text("RMSSD:" + str(self._rmssd), 0, 20, 1)
        oled.oled.text("SDNN:"  + str(self._sdnn),  0, 30, 1)
        oled.oled.text("SNS:"   + str(self._sns),   0, 42, 1)
        oled.oled.text("PNS:"   + str(self._pns),   0, 52, 1)
        oled.oled.show()
        print("KUBIOS RESPONSE", self.history_response())

    def history_response(self):
        '''
        Return the current Kubios DATA as a dictionary for cloud storage.
 
        Returns:
            dict with keys: Time, Mean PPI, Mean BPM, RMMDS, SDNN, SNS, PNS.
        '''
        return {
            "Time": self._time,
            "Mean PPI": self._ppi,
            "Mean BPM": self._bpm,
            "RMMDS": self._rmssd,
            "SDNN": self._sdnn,
            "SNS": self._sns,
            "PNS": self._pns
        }
        


    def save_json_to_pico(self, filename, data):
        # Serialize and write the response JSON to a file on the Pico filesystem
        with open(filename, "w") as file:
            json.dump(data, file)


class Wifi:
    def __init__(self):   
        self.selected_ssid = ""
        self.password = ""
        self._wlan = network.WLAN(network.STA_IF)
        self.mac = 0

    def get_pico_mac(self):
        mac_bytes = self._wlan.config("mac")
        self.mac = ubinascii.hexlify(mac_bytes).decode().upper()
        return self.mac

    def wifi_ana(self):
        self.selected_ssid = "Tkach"
        self.password = "Gesku0911"
    
    def default_wifi(self):
        self.selected_ssid = "KME751_Group_8"
        self.password = "TkachGrantLay"

    def wifi_on(self):
        time.sleep_ms(100)
        self._wlan.active(True)
        print("CONF", self.selected_ssid, self.password)
        
        if not self._wlan.isconnected():
            print("Connecting to Wi-Fi...")
            self._wlan.connect(self.selected_ssid, self.password)

            max_wait = 10 
            while max_wait > 0:
                if self._wlan.isconnected():
                    break 
                max_wait -= 1
                print("Waiting for connection...")
                time.sleep(1) 

            if not self._wlan.isconnected():
                print("Wi-Fi Connection FAILED! Check password or router.")
                return None
                

        print("Connected to SSID:", self._wlan.config('ssid'))
        print("Wi-Fi connected, IP:", self._wlan.ifconfig()[0])
        return self._wlan

    def wifi_off(self):
        self._wlan.active(False)


class MQTT:
    # Broker connection settings
    BROKER_IP = "194.110.232.94"
    BROKER_PORT = 1883

    # Publish topics for different database operations
    REQUEST_DEVISE = b"database/devices/add"
    REQUEST_ADD_PATIENT = b"database/patients/add"
    REQUEST_LIST_PATIENT = b"database/patients/list"
    REQUEST_ADD_RECORDS = b"database/records/add"


    RESPONSE_TOPIC = b"database/response"
    TIMEOUT_MS = 15000                      # Max wait time for a response (15 seconds)
    
    def __init__(self):
        self.patient = ""
        self.patient_id = 0
        self.latest_response = None     # Stores the most recent parsed response
        self.mqtt_client = None

    def setup_client(self, mac):
        # Initialize the MQTT client with device MAC address as a client ID
        self.mqtt_client = MQTTClient(
            client_id=(mac + "_ext").encode(),
            server=self.BROKER_IP, 
            port=self.BROKER_PORT)
        self.mqtt_client.set_callback(self._mqtt_callback)
        return self.mqtt_client


    def _safe_publish(self, topic, payload):
        '''Helper method to handle disconnected sockets (EBADF)'''
        if not self.mqtt_client:
            return False
            
        try:
            self.mqtt_client.publish(topic, json.dumps(payload))
            return True
        except OSError as e:
            print(f"Connection lost during publish (Error {e}). Reconnecting...")
            try:
                # If the socket is dead, reconnect and try exactly one more time
                self.connect_and_subscribe()
                self.mqtt_client.publish(topic, json.dumps(payload))
                return True
            except OSError:
                print("Failed to publish even after reconnecting.")
                return False

    def _mqtt_callback(self, topic, msg):
        # Ignore messages from topics other than the response topic
        if topic != self.RESPONSE_TOPIC:
            return
        try:
            # Parse the incoming JSON message and store it
            self.latest_response = json.loads(msg)
        except ValueError:      
            self.latest_response = None

    def connect_and_subscribe(self):
        gc.collect()
        # Connect to the MQTT broker and subscribe to the response topic
        self.mqtt_client.connect()
        self.mqtt_client.subscribe(self.RESPONSE_TOPIC)
    
    def add_device(self, mac):
        payload = {
            "mac": mac,
            "device_name": "Group 8"
        }

        if self.mqtt_client:
            self._safe_publish(self.REQUEST_DEVISE, payload)

    def add_patient(self, client_name, mac):
        payload = {
            "mac": mac,
            "patient_name": client_name
        }

        if self.mqtt_client:
            self._safe_publish(self.REQUEST_ADD_PATIENT, payload)
        
    
    def list_patients(self, mac):
        payload = {
            "mac": mac
        }

        if self.mqtt_client:
            self._safe_publish(self.REQUEST_LIST_PATIENT, payload)

    def add_records(self, client_id, payload, mac):
        self.latest_response = None

        timestamp = payload.get("Time", "N/A")
        hr = payload.get("Mean BPM", "N/A")
        ppi = payload.get("Mean PPI", "N/A")
        rmssd = payload.get("RMMDS", "N/A")
        sdnn = payload.get("SDNN", "N/A")
        sns = payload.get("SNS", "N/A")
        pns = payload.get("PNS", "N/A")

        f_payload = {
            "mac": mac,
            "timestamp": timestamp,
            "mean_hr": hr,
            "mean_ppi": ppi,
            "rmssd": rmssd,
            "sdnn": sdnn,
            "sns": sns,
            "pns": pns,
            "patient_id": client_id
        }

        if self.mqtt_client:
            self._safe_publish(self.REQUEST_ADD_RECORDS, f_payload)


    def wait_for_response(self):
        '''
        Wait for incoming messages until a response arrives or the timeout is over

        Returns:
            dict | None: The parsed Kubios response, or None on timeout.
        '''
        start = time.ticks_ms()

        while time.ticks_diff(time.ticks_ms(), start) < self.TIMEOUT_MS:
            self.mqtt_client.check_msg()
            
            if self.latest_response:
                print("Response received:")
                print("MQQT database response: ", self.latest_response)
                break
            time.sleep_ms(200)  # Short delay to avoid busy-waiting

        return self.latest_response

    def disconnect(self):
        self.mqtt_client.disconnect()
        print("Client disconnected")


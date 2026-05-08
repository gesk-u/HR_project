# Pico Health Monitor Pulse Before Brew (PB4B) 
A heart rate and HRV (Heart Rate Variability) monitoring device built on the Raspberry Pi Pico W.  
Measures HR, calculates RMSSD and SDNN locally, and can send data to the Kubios cloud for advanced analysis.

---

## Hardware Required
 
| Part | Details |
|---|---|
| Raspberry Pi Pico W | Must be the **W** (Wi-Fi) version for Kubios cloud analysis |
| PPG sensor | Connected to ADC pin **GPIO 27** |
| OLED display | SSD1306, 128×64, I2C — SDA on **GPIO 14**, SCL on **GPIO 15** |
| Rotary encoder | A = **GPIO 10**, B = **GPIO 11**, Push = **GPIO 12** |
| LED indicator | **GPIO 22** — flashes on each detected heartbeat |
| Button – Accept | **GPIO 7** |
| Button – Remove | **GPIO 9** |

---
 
## Installation — Step by Step
 
### Step 1 — Install Python on your PC
 
1. Go to **https://www.python.org/downloads**
2. Download and run the installer
3. **Important:** tick **"Add Python to PATH"** during installation
---
 
### Step 2 — Install mpremote
 
Open **Command Prompt** (search for `cmd` in the Start menu) and run:
 
```
pip install mpremote
```
 
mpremote is the tool that transfers files to the Pico over USB.
 
---
 
### Step 3 — Flash MicroPython onto the Pico
 
The Pico needs MicroPython firmware before any code can run on it.
 
1. Hold the **BOOTSEL** button on the Pico W
2. While holding it, plug the USB cable into your PC
3. A drive called **RPI-RP2** will appear — like a USB stick
4. Go to **https://micropython.org/download/RPI_PICO_W/** and download the latest `.uf2` file
5. Drag and drop the `.uf2` file onto the **RPI-RP2** drive
6. The Pico will restart automatically — the drive disappears, which means it worked
---
 
### Step 4 — Run the Installer
 
1. Copy the project folder to anywhere on your PC
2. Make sure the Pico is **not** plugged in yet
3. Double-click **install.cmd**
4. When prompted, plug in the Pico and press any key
5. The script uploads all files and installs the required libraries automatically
6. When it says **"Done!"**, close the window
---
 
### Step 5 — Use the Device
 
- Unplug the Pico and plug it back in (without holding BOOTSEL)
- The intro animation plays automatically — press the rotary encoder button to skip to the menu
- Rotate the encoder to move between options, push to select
---

---
 
## Controls
 
| Control | Action |
|---|---|
| Rotate encoder | Move menu cursor up / down |
| Push encoder | Confirm selection / add character (in name entry) |
| Accept button (GPIO 7) | Confirm name entry |
| Remove button (GPIO 9) | Delete last character (backspace) |
| Push encoder during measurement | Stop recording and return to menu |
 
---
## How Measurements Work
 
1. Place your fingertip gently on the PPG sensor
2. Hold still — movement causes noise in the signal
3. The device detects heartbeats using an adaptive threshold on the PPG waveform
4. PPI (time between beats) is calculated from each beat timestamp
5. Artifacts (unusually large PPI jumps) are filtered out automatically
6. BPM, RMSSD, and SDNN are calculated from the cleaned PPI list
**RMSSD** measures short-term variability (parasympathetic activity).  
**SDNN** measures overall variability (total autonomic activity).
 
---
## Local History
 
After a **Basic HRV** measurement, press the encoder button to save the result.  
Data is stored in `localhistory.json` on the Pico's flash memory under your username.  
Browse saved sessions from the **History** menu option.
 
---
 
## Kubios Cloud Analysis
 
The **Kubios** option connects to Wi-Fi and sends your PPI data to the Kubios HRV cloud service.  
It returns: Mean HR, Mean PPI, RMSSD, SDNN, SNS index, and PNS index.
 
> **Note:** Wi-Fi credentials are set inside `Con.py`. Update `selected_ssid` and `password` before installing.
 
---
 
## Project Files
 
| File | Purpose |
|---|---|
| `main.py` | Main application — state machine and hardware initialisation |
| `Con.py` | Wi-Fi credentials and connection settings |
| `Input.py` | User name entry logic |
| `cross.py` | Additional UI or helper functions |
| `intro.py` | Intro animation frames |
| `media.py` | Pixel-art bitmaps and display assets |
| `OOPs.py` | Supporting classes |
| `client_ids.json` | Saved user names |
| `localhistory.json` | Local HRV session history |
 
---
## Troubleshooting
 
**install.cmd says "mpremote not found"**  
→ Make sure Python was installed with "Add to PATH" ticked, then rerun `pip install mpremote` in CMD.
 
**RPI-RP2 drive does not appear**  
→ Make sure you are holding BOOTSEL *before* plugging in the USB cable.
 
**OLED stays blank during measurement**  
→ Check that the PPG sensor is connected to GPIO 27 and that the finger is placed flat on the sensor.
 
**Kubios returns no response**  
→ Check Wi-Fi credentials in `Con.py` and make sure you are within range of the network.


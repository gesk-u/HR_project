from Con import Kubios, Wifi, MQTT
from OOPs import OLED, Data, User_input, History, App
from Input import Btn, Rotary_encoder, HR_sensor



# ---------------------------------------------------------------------------
# Hardware initialisation
# ---------------------------------------------------------------------------

accept_btn = Btn(7)
remove_btn = Btn(9) 
rot = Rotary_encoder(30, 10, 11, 12)
oled = OLED(128, 64)
av = HR_sensor(250, 27)

mqtt = MQTT()
wifi_manager = Wifi()
kubios = Kubios()
data = Data(av)
history = History(oled)
user_selection = User_input(history, oled)
client = None

app = App(client, oled, data, rot, kubios, mqtt, history, wifi_manager, accept_btn, remove_btn)
app.oled.show_menu(app.menu_item)


# ---------------------------------------------------------------------------
# Main state-machine loop
# ---------------------------------------------------------------------------
app.state = 0

while True:
    # State 0: power-off
    if app.state == 0:
        app.state_off()
        if app.check_btn_press():
            app._btn_val = False  # Fixed: changed from btn_val to _btn_val
            app.state = 1

    # State 1: intro animation
    elif app.state == 1:
        app.anim_state()
        if app.check_btn_press():
            app._btn_val = False  # Fixed
            app.state = 10

    # State 2: main menu. Spin until a selection
    elif app.state == 2:
        while True:
            app.state_menu()
            if app._btn_val:      # Fixed
                app._btn_val = False # Fixed
                break
        app.data.reset() 

    # State 3: countdown animation before live HR measurement
    elif app.state == 3:
        app.state_3a()
    
    # State 4: live HR measurement (free-running)
    elif app.state == 4:
        app.state_3b()
        app.state = 2

    # State 5: fixed-window HRV recording
    elif app.state == 5:
        app.state_5()
        if app.check_btn_press():
            reading = app.data.hrv_history()
            app.history.local_add(app.client, reading)
            app.state_off()
            app.state = 2
            app._btn_val = False  # Fixed

    # State 6: coffee readiness
    elif app.state == 6:
        if app._coffee_state() == True:
            oled.coffeegood(app.rot.push_fifo)
        else:
            oled.coffeebad(app.rot.push_fifo)
        if app.check_btn_press():
            app._btn_val = False
            app.state = 2
    
    # State 7: Kubios cloud HRV analysis
    elif app.state == 7:
        app.state_7()

    # State 8: local history browser
    elif app.state == 8:
        app.history.local_load(app.client)
        app.history.make_options()
        app.state = app.history.show_history(app.rot, app.oled)
    
    # State 9: shutdown screen
    elif app.state == 9:
        app.state_off()
        if app.check_btn_press():
            app._btn_val = False  # Fixed
            app.state = 1

    # State 10: client Selection
    elif app.state == 10:
        next_state = user_selection.show_names(app.rot, app.oled, app.accept_btn, app.remove_btn, app.mqtt, app.mac)
        app.client = user_selection.selected_name
        app.client_id = user_selection.client_ids.get(app.client, 0) 
        print(f"Active client set to: {app.client} (ID: {app.client_id})")
        app.state = next_state
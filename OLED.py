from machine import Pin, PWM, I2C, ADC
from ssd1306 import SSD1306_I2C
from fifo import Fifo
import time
from piotimer import Piotimer
from led import Led
import media

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
            for row_i, row in enumerate(media.Small_Coffee):
                for col_i, c in enumerate(row):
                    self.oled.pixel(col_i, row_i, c)
                    
        self.oled.show()
        


        
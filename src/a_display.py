import machine

from machine import Pin, I2C

import sh1106
import math

TICKS_PER_SECOND:int = 30

def ticks_to_seconds_left(value: int) -> int:
    return math.ceil((value + TICKS_PER_SECOND-1)/TICKS_PER_SECOND)

def ticks_to_seconds(value: int) -> int:
    return round(value/TICKS_PER_SECOND)

def scan(i2c: I2C):
    devices = i2c.scan()

    if len(devices) != 0:
        print('Number of I2C devices found=',len(devices))
        for device in devices:
            print("Device Hexadecimal Address= ",hex(device))
    else:
        print("No device found")
        

def initialize_button() -> Button:
    pin: Pin = Pin(13, Pin.IN, Pin.PULL_UP)
    return Button(pin)

class Button:
    def __init__(self, pin: Pin):
        self.pin = pin
    
    def is_pressed(self):
        a = self.pin.value()
        return not a # it is inverted
        
class GamePhase:
    def tick(self, button: Button) -> Bool:
        raise NotImplementedError("must be defined by GamePhases")
    
    
        
class MainMenu(GamePhase):
    def tick(self, button: Button):
        return button.is_pressed()


SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
BALL_SIZE = 16
WALL_SIZE = 1

class InGame(GamePhase):
    def __init__(self):
        self.button_was_down_last_tick: bool = False
        self.direction_x: int = 1
        self.direction_y: int = 1
        self.speed: int = 2
        self.right_side = SCREEN_WIDTH - BALL_SIZE - WALL_SIZE
        self.left_side = WALL_SIZE
        self.lower_side = SCREEN_HEIGHT - BALL_SIZE - WALL_SIZE
        self.upper_side = 0
        self.x : int = self.left_side
        self.y : int = self.upper_side
        self.speed_increase_every: int = TICKS_PER_SECOND * 2
        self.tick_count: int = 0

        
    def tick(self, button: Button):
        self.tick_count += 1
        
        next_x: int = self.x + self.direction_x * self.speed
        if next_x >= self.right_side:
            self.direction_x = -1
            next_x = self.right_side
        elif next_x <= self.left_side:
            self.direction_x = 1
            next_x = self.left_side
        self.x = next_x
        
        next_y: int = self.y + self.direction_y * self.speed
        if next_y >= self.lower_side:
            self.direction_y = -1
            next_y = self.lower_side
        elif next_y <= self.upper_side:
            self.direction_y = 1
            next_y = self.upper_side
        self.y = next_y
        
            
            
        if self.tick_count % self.speed_increase_every == 0:
            self.speed += 1
            
            
        button_is_pressed_now = button.is_pressed()
        
        if button_is_pressed_now and not self.button_was_down_last_tick:
            print("button went down")
            
        self.button_was_down_last_tick = button_is_pressed_now

class CountDown(GamePhase):
    def __init__(self, count_down: int):
        self.count_down = count_down
        
    def tick(self, button: Button):
        if self.count_down == 0:
            return True
        
        self.count_down -= 1


class Game:
    def __init__(self):
        self.is_over: bool = False
        self.phase = MainMenu()


    def switch_phase(self) -> GamePhase:
        phase: GamePhase = self.phase
        if isinstance(phase, MainMenu):
            return CountDown(120)
        elif isinstance(phase, CountDown):
            return InGame()
        elif isinstance(phase, InGame):
            return MainMenu()
        else:
            return "Unknown type"
    
    def tick(self, button: Button):
        is_done: Bool = self.phase.tick(button)
        if is_done:
            self.phase = self.switch_phase()
            
                
class Render:
    def __init__(self, display: SH1106_I2C):
        self.display = display
        
    def render_main_menu(self, main: MainMenu):
        self.display.text('Main Menu', 0, 32, 1)
        
    def render_count_down(self, count_down: CountDown):
        self.display.text('Get Ready!', 0, 32, 1)
        self.display.text(str(ticks_to_seconds(count_down.count_down)), 0, 48, 1)
    
    def render_ingame(self, ingame: InGame):
        #self.display.text('Hello World!', 128 - ingame.x, 32, 1)
        
        self.display.vline(0, 0, 64, 1)
        self.display.vline(127, 0, 64, 1)
        self.display.fill_rect(ingame.x, ingame.y, BALL_SIZE, BALL_SIZE, 1)
        
        
    def render(self, phase: GamePhase):
        self.display.fill(0)
        if isinstance(phase, MainMenu):
            self.render_main_menu(phase)
        elif isinstance(phase, CountDown):
            self.render_count_down(phase)
        elif isinstance(phase, InGame):
            self.render_ingame(phase)
        self.display.show()


def initialize_i2c() -> I2C:
    sdaPIN = Pin(2)
    sclPIN = Pin(3)
    i2c = I2C(1,sda=sdaPIN, scl=sclPIN, freq=400000)
    return i2c

def initialize_display() -> SH1106_I2C:
    display : SH1106_I2C = sh1106.SH1106_I2C(128,64,i2c)
    display.sleep(False)
    return display

i2c: I2C = initialize_i2c()

display: SH1106_I2C = initialize_display()

button: Button = initialize_button()

scan(i2c)

game: Game = Game()
render: Render = Render(display)

while not game.is_over:
    game.tick(button)
    render.render(game.phase)

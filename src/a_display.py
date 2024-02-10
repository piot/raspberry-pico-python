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
BALL_SIZE = 8
WALL_SIZE = 1
MIDDLE_X = 64


class Rating():
    ARE_YOU_SERIOUS = 0
    TOO_EARLY = 1
    OK = 2 
    PERFECT = 3
    AWESOME = 4
    
    @staticmethod
    def str_value(rating_value):
        rating_map = {
            Rating.ARE_YOU_SERIOUS: "Are you SERIOUS?",
            Rating.TOO_EARLY: "Too Early",
            Rating.OK: "Ok, I take it",
            Rating.PERFECT: "Perfect!",
            Rating.AWESOME: "AWESOME!",
        }
        return rating_map.get(rating_value, str(rating_value))
 
    

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
        self.speed_increase_every: int = TICKS_PER_SECOND * 10
        self.tick_count: int = 0
        self.ball_bounce_count: int = 0
        self.last_rating: Rating = Rating.OK
        self.last_points_given: int = 0
        self.points: int = 0
        self.rating_direction: int = 1
        self.rating_count: int = 0


    def check_bounce_against_walls(self) -> None:
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
    
    def distance_to_cloest_wall(self) -> int:
        distance_to_left = self.x - self.left_side
        distance_to_right = self.right_side - self.x
        return min(distance_to_left, distance_to_right)

    @staticmethod
    def rating_from_distance_to_wall(distance: int) -> Rating:
        if distance > 30:
            return Rating.ARE_YOU_SERIOUS
        elif distance > 15:
            return Rating.TOO_EARLY
        elif distance > 10:
            return Rating.OK
        elif distance > 5:
            return Rating.PERFECT
        return Rating.AWESOME

    def ball_bounced_from_button_press(self):
        self.direction_x = -self.direction_x
        self.direction_y = -self.direction_y
        self.ball_bounced()

    def rate_button_press(self) -> None:
        wall_distance = self.distance_to_cloest_wall()
        points = 50 - wall_distance
        self.last_points_given = points
        self.points += points
        self.last_rating = InGame.rating_from_distance_to_wall(wall_distance)
        self.rating_count += 1
        self.rating_direction = -1 if self.x <= MIDDLE_X else 1

    def allowed_to_be_rated(self) -> bool:
        return self.rating_direction == 0
    
    def button_went_down(self):
        if self.allowed_to_be_rated():
            self.rate_button_press()
        else:
            print("not allowed to be rated", self.x, self.rating_direction)
        
    def check_if_allowed_to_be_rated_again(self):
        if (self.rating_direction > 0 and self.x <= MIDDLE_X) or (self.rating_direction < 0 and self.x > MIDDLE_X):
            self.rating_direction = 0
        
    def check_if_speed_should_increase(self):
        if self.tick_count % self.speed_increase_every == 0:
            self.speed += 1
            
    def check_if_button_is_pressed(self):
        button_is_pressed_now = button.is_pressed()
        if button_is_pressed_now and not self.button_was_down_last_tick:
            self.button_went_down()
        self.button_was_down_last_tick = button_is_pressed_now

    def tick(self, button: Button):
        self.tick_count += 1
        
        self.check_bounce_against_walls()
        self.check_if_allowed_to_be_rated_again()
        self.check_if_speed_should_increase()            
        self.check_if_button_is_pressed()


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
            return CountDown(10)
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
        self.last_shown_rating_count: int = 0
        self.show_rating_timer: int = 0
        
    def render_main_menu(self, main: MainMenu):
        self.display.text('Main Menu', 0, 32, 1)
        
    def render_count_down(self, count_down: CountDown):
        self.display.text('Get Ready!', 0, 32, 1)
        self.display.text(str(ticks_to_seconds(count_down.count_down)), 0, 48, 1)
    
    def render_rating(self, rating: Rating, points_given: int):
        self.display.text(Rating.str_value(rating), 0, 15, 1)
        self.display.text("bonus:" + str(points_given), 0, 32, 1)
        
    def render_score(self, points_total: int) -> None:
        self.display.text("total:" + str(points_total), 0, 48, 1)

    def render_ingame(self, ingame: InGame):
        #self.display.text('Hello World!', 128 - ingame.x, 32, 1)
        if self.last_shown_rating_count != ingame.rating_count:
            self.show_rating_timer = TICKS_PER_SECOND * 0.5
            self.last_shown_rating_count = ingame.rating_count
            
        if self.show_rating_timer > 0:
            self.show_rating_timer -= 1
            self.render_rating(ingame.last_rating, ingame.last_points_given)
        self.render_score(ingame.points)
        
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

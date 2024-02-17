import machine

from machine import Pin, I2C, PWM

import sh1106
import math
import time

TICKS_PER_SECOND: int = 30


def ticks_to_seconds_left(value: int) -> int:
    return math.ceil((value + TICKS_PER_SECOND - 1) / TICKS_PER_SECOND)


def ticks_to_seconds(value: int) -> int:
    return round(value / TICKS_PER_SECOND)


def scan(i2c: I2C):
    devices = i2c.scan()

    if len(devices) != 0:
        print("Number of I2C devices found=", len(devices))
        for device in devices:
            print("Device Hexadecimal Address= ", hex(device))
    else:
        print("No device found")


class Button:
    def __init__(self, pin: Pin):
        self.pin = pin

    def is_pressed(self):
        a = self.pin.value()
        return not a  # it is inverted


SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
BALL_SIZE = 8
WALL_SIZE = 1
MIDDLE_X = 64

class RGBLed:
    def __init__(self, red: Pin, green: Pin, blue: Pin):
        self.red_pwm = RGBLed.setup_pwm(red)
        self.green_pwm = RGBLed.setup_pwm(green)
        self.blue_pwm = RGBLed.setup_pwm(blue)
        self.turn_off()
    
    @staticmethod
    def setup_pwm(pin: Pin) -> PWM:
        RGB_FREQUENCY = 10000
        pwm = PWM(pin)
        pwm.freq(RGB_FREQUENCY)
        return pwm
    
    def set_values(self, red: int, green: int, blue: int):
        self.red_pwm.duty_u16(65535 - red)
        self.green_pwm.duty_u16(65535 - green)
        self.blue_pwm.duty_u16(65535 - blue)
        
    def set_color(self, colors: Tuple[float, float, float]) -> None:
        red = round(colors[0] * 65535)
        green = round(colors[1] * 65535)
        blue = round(colors[2] * 65535)
        self.set_values(red, green, blue)
        
    def turn_off(self) -> None:
        self.set_values(0,0,0)

class Rating:
    ARE_YOU_SERIOUS = 0
    NOT_CLOSE = 1
    OK = 2
    PERFECT = 3
    AWESOME = 4

    @staticmethod
    def str_value(rating_value):
        rating_map = {
            Rating.ARE_YOU_SERIOUS: "Are you SERIOUS?",
            Rating.NOT_CLOSE: "Not even close",
            Rating.OK: "Ok, I take it",
            Rating.PERFECT: "Perfect!",
            Rating.AWESOME: "AWESOME!",
        }
        return rating_map.get(rating_value, str(rating_value))


class GamePhase:
    def tick(self, button: Button) -> Bool:
        raise NotImplementedError("must be defined by GamePhases")


class MainMenu(GamePhase):
    def __init__(self):
        self.was_pressed = True

    def tick(self, button: Button):
        is_pressed = button.is_pressed()
        if is_pressed and not self.was_pressed:
            return True
        self.was_pressed = is_pressed


class CountDown(GamePhase):
    def __init__(self, count_down: int):
        self.count_down = count_down

    def tick(self, button: Button):
        if self.count_down == 0:
            return True

        self.count_down -= 1


class InGame(GamePhase):
    def __init__(self):
        self.button_was_down_last_tick: bool = True
        self.direction_x: int = 1
        self.direction_y: int = 1
        self.speed: int = 2
        self.right_side = SCREEN_WIDTH - BALL_SIZE - WALL_SIZE
        self.left_side = WALL_SIZE
        self.lower_side = SCREEN_HEIGHT - BALL_SIZE - WALL_SIZE
        self.upper_side = 0
        self.x: int = self.left_side
        self.y: int = self.upper_side
        self.speed_increase_every: int = TICKS_PER_SECOND * 3
        self.last_rating: Rating = Rating.OK
        self.last_bonus_given: int = 0
        self.score: int = 0
        self.rating_direction: int = 1
        self.rating_count: int = 0
        self.ticks_left: int = TICKS_PER_SECOND * 20

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
        if distance > 25:
            return Rating.ARE_YOU_SERIOUS
        elif distance > 20:
            return Rating.NOT_CLOSE
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
        score: int = round(MIDDLE_X / 2 - wall_distance)
        if score > 0:
            score = round(score ** 1.5 / 8)
        self.last_bonus_given = score
        self.score += score
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
        if (self.rating_direction > 0 and self.x <= MIDDLE_X) or (
            self.rating_direction < 0 and self.x > MIDDLE_X
        ):
            self.rating_direction = 0

    def check_if_speed_should_increase(self):
        if self.ticks_left % self.speed_increase_every == 0:
            self.speed += 1

    def check_if_button_is_pressed(self):
        button_is_pressed_now = button.is_pressed()
        if button_is_pressed_now and not self.button_was_down_last_tick:
            self.button_went_down()
        self.button_was_down_last_tick = button_is_pressed_now

    def tick(self, button: Button):
        if self.ticks_left == 0:
            return True
        self.ticks_left -= 1

        self.check_bounce_against_walls()
        self.check_if_allowed_to_be_rated_again()
        self.check_if_speed_should_increase()
        self.check_if_button_is_pressed()


class GameOver(GamePhase):
    def __init__(self, score: int):
        self.score = score
        self.was_pressed = True
        self.ticks_left: int = TICKS_PER_SECOND * 1

    def tick(self, button: Button):
        if self.ticks_left == 0:
            is_pressed = button.is_pressed()
            if is_pressed and not self.was_pressed:
                return True
            self.was_pressed = is_pressed
        else:
            self.ticks_left -= 1


class Game:
    def __init__(self):
        self.is_over: bool = False
        self.phase = MainMenu()

    def switch_phase(self) -> GamePhase:
        phase: GamePhase = self.phase
        if isinstance(phase, MainMenu):
            return CountDown(TICKS_PER_SECOND * 2)
        elif isinstance(phase, CountDown):
            return InGame()
        elif isinstance(phase, InGame):
            return GameOver(phase.score)
        elif isinstance(phase, GameOver):
            return MainMenu()
        else:
            return "Unknown type"

    def tick(self, button: Button):
        is_done: Bool = self.phase.tick(button)
        if is_done:
            self.phase = self.switch_phase()


class RenderPhase:
    def __init__(self, display: SH1106_I2C, rgb_led: RGBLed=None):
        self.display = display

    def tick(self, button: Button) -> Bool:
        raise NotImplementedError("must be defined by GamePhases")


class RenderInGame(RenderPhase):
    def __init__(self, display: SH1106_I2C, rgb_led: RGBLed):
        self.display = display
        self.rgb_led = rgb_led
        self.last_shown_rating_count: int = 0
        self.show_rating_timer: int = 0

    def render_rating(self, rating: Rating, score_given: int):
        self.display.text(Rating.str_value(rating), 0, 5, 1)
        self.display.text("bonus:" + str(score_given), 14, 22, 1)

    def render_score(self, score: int) -> None:
        self.display.text("Score " + str(score), 30, 48, 1)

    def render_ticks_left(self, ticks: int) -> None:
        self.display.text("Time Left " + str(ticks), 10, 38, 1)
        
    def set_led_color_from_rating(self, rating: Rating):
        if rating == Rating.ARE_YOU_SERIOUS:
            color = (1, 0.1, 0.1)
        elif rating == Rating.NOT_CLOSE:
            color = (0.5, 0.3, 0.3)
        elif rating == Rating.OK:
            color = (0.4,0.4,0.1)
        elif rating == Rating.PERFECT:
            color = (0.1,0.5,0.1)
        elif rating == Rating.AWESOME:
            color = (0.1, 1, 0.1)
            
        self.rgb_led.set_color(color)

    def render(self, ingame: InGame):
        # self.display.text('Hello World!', 128 - ingame.x, 32, 1)
        if self.last_shown_rating_count != ingame.rating_count:
            self.show_rating_timer = TICKS_PER_SECOND * 0.5
            self.last_shown_rating_count = ingame.rating_count
            self.set_led_color_from_rating(ingame.last_rating)

        if self.show_rating_timer > 0:
            self.show_rating_timer -= 1
            if self.show_rating_timer == 0:
                self.rgb_led.turn_off()
            self.render_rating(ingame.last_rating, ingame.last_bonus_given)
            
        self.render_score(ingame.score)

        if ingame.ticks_left < 100:
            self.render_ticks_left(ingame.ticks_left)

        self.display.vline(0, 0, 64, 1)
        self.display.vline(127, 0, 64, 1)
        self.display.fill_rect(ingame.x, ingame.y, BALL_SIZE, BALL_SIZE, 1)
        
    def close(self):
        self.rgb_led.turn_off()


class RenderMainMenu(RenderPhase):
    def render(self, main: MainMenu):
        self.display.text("Reaction Game", 15, 20, 1)
        self.display.text("press button", 12, 52, 1)


class RenderGameOver(RenderPhase):
    def render(self, game_over: GameOver) -> None:
        self.display.text("GAME OVER", 30, 20, 1)
        self.display.text("Score " + str(game_over.score), 32, 34, 1)
        if game_over.ticks_left == 0:
            self.display.text("press button", 12, 52, 1)


class RenderCountDown(RenderPhase):
    def render(self, count_down: CountDown):
        self.display.text("Get Ready!", 20, 12, 1)
        self.display.text(str(ticks_to_seconds(count_down.count_down)), 60, 35, 1)


class Render:
    def __init__(self, display: SH1106_I2C, rgb_led: RGBLed):
        self.display = display
        self.rgb_led = rgb_led
        self.phase: RenderPhase = None

    def switch_render_phase_if_needed(self, phase: GamePhase):
        if isinstance(phase, MainMenu) and not isinstance(self.phase, RenderMainMenu):
            self.phase = RenderMainMenu(self.display)
        elif isinstance(phase, CountDown) and not isinstance(self.phase, RenderCountDown):
            self.phase = RenderCountDown(self.display)
        elif isinstance(phase, InGame) and not isinstance(self.phase, RenderInGame):
            self.phase = RenderInGame(self.display, self.rgb_led)
        elif isinstance(phase, GameOver) and not isinstance(self.phase, RenderGameOver):
            self.phase.close()
            self.phase = RenderGameOver(self.display)

    def render(self, phase: GamePhase):
        self.display.fill(0)
        self.switch_render_phase_if_needed(phase)
        self.phase.render(phase)
        self.display.show()


def initialize_i2c(sda_pin: Pin, scl_pin: Pin) -> I2C:
    i2c = I2C(1, sda=sda_pin, scl=scl_pin, freq=400000)
    return i2c


def initialize_display() -> SH1106_I2C:
    display: SH1106_I2C = sh1106.SH1106_I2C(128, 64, i2c)
    display.sleep(False)
    return display


# All pins used on the board. I2C is for the display
i2c_sda_pin = Pin(2)
i2c_scl_pin = Pin(3)
rgb_led_red_pin = Pin(10)
rgb_led_green_pin = Pin(11)
rgb_led_blue_pin = Pin(12)
button_pin = Pin(13, Pin.IN, Pin.PULL_UP)
# --------------------------

i2c = initialize_i2c(i2c_sda_pin, i2c_scl_pin)
display = initialize_display()
button = Button(button_pin)
rgb_led = RGBLed(rgb_led_red_pin, rgb_led_green_pin, rgb_led_blue_pin)

# scan(i2c)
game = Game()
render = Render(display, rgb_led)

while not game.is_over:
    game.tick(button)
    render.render(game.phase)

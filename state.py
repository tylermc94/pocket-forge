import time
import threading
from PIL import Image, ImageDraw


class AppState:
    MAIN             = "main"
    MAIN_MENU        = "main_menu"
    SETTINGS_MENU    = "settings_menu"
    GAMES_MENU       = "games_menu"
    POWER_MENU       = "power_menu"
    PARTY_MODE       = "party_mode"
    OTA_CONFIRM      = "ota_confirm"
    OTA_RESULT       = "ota_result"
    VOLUME           = "volume"
    BRIGHTNESS       = "brightness"
    SENSITIVITY      = "sensitivity"
    ABOUT            = "about"
    DRAWING          = "drawing"
    SNAKE            = "snake"
    POWER_CONFIRM    = "power_confirm"


# Canvas
img  = Image.new('RGB', (240, 280), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

# App state
current_state      = AppState.MAIN
menu_index         = 0
prev_menu_index    = -1
scroll_accumulator = 0

# Menu item lists
main_menu_items     = ["Status", "Settings", "Games", "Power", "About"]
settings_menu_items = ["Volume", "Brightness", "Trackball Sensitivity", "Screen Timeout", "Developer Options", "< Back"]
games_menu_items    = ["Party Mode", "Snake", "Pong", "Drawing", "< Back"]
power_menu_items    = ["Sleep", "Power Off", "Restart", "< Back"]

current_menu_items = main_menu_items

# Click detection
last_click_time       = 0
click_start_time      = 0
movement_during_click = 0
MOVEMENT_THRESHOLD    = 3
SCROLL_SENSITIVITY    = 5

# Volume / brightness / sensitivity state
current_volume          = 50
current_brightness      = 100
trackball_sensitivity   = 5    # 1-10; maps to SCROLL_SENSITIVITY = 11 - value
screen_timeout_minutes  = 1    # minutes; options: 1, 2, 5, Never

# Party mode state
party_active = False
party_speed  = 30       # steps/sec, range 10-100
party_hue    = 0.0
party_lock   = threading.Lock()
party_thread = None     # Keep reference so we can join it

# Battery state
_battery_level = None
_battery_lock  = threading.Lock()

# Sleep / wake state
sleeping          = False
sleep_time        = 0.0
last_activity_time = time.time()

# LED color tracking (so we can restore after sleep/timeout)
led_color = (0, 0, 0)

# Power confirm action: "poweroff" or "reboot"
power_confirm_action = None

# Drawing game state
drawing_cursor_x = 120
drawing_cursor_y = 140
drawing_pixels   = []   # list of (x, y) tuples

# Snake game state
snake_body      = []    # list of (x, y) grid positions
snake_dir       = (1, 0)
snake_food      = (0, 0)
snake_score     = 0
snake_speed     = 0.15  # seconds per step
snake_last_step = 0.0
snake_paused    = False
snake_dead      = False
snake_foods_eaten = 0


def get_battery_level():
    with _battery_lock:
        return _battery_level

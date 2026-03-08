import threading
import time
from PIL import Image, ImageDraw


class AppState:
    MAIN          = "main"
    MAIN_MENU     = "main_menu"
    SETTINGS_MENU = "settings_menu"
    GAMES_MENU    = "games_menu"
    POWER_MENU    = "power_menu"
    PARTY_MODE    = "party_mode"
    DRAWING       = "drawing"
    ABOUT                 = "about"
    VOLUME                = "volume"
    BRIGHTNESS            = "brightness"
    TRACKBALL_SENSITIVITY = "trackball_sensitivity"
    SCREEN_TIMEOUT        = "screen_timeout"
    DEV_OPTIONS           = "dev_options"
    SNAKE                 = "snake"
    POWER_CONFIRM         = "power_confirm"
    RECORDING             = "recording"
    TRANSCRIBING          = "transcribing"


# Canvas
img  = Image.new('RGB', (240, 280), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

# App state
current_state      = AppState.MAIN
menu_index         = 0
prev_menu_index    = -1
scroll_accumulator = 0

# Menu item lists
main_menu_items     = ["Status", "About", "Settings", "Games", "Power"]
settings_menu_items = ["Volume", "Brightness", "Trackball Sensitivity", "Screen Timeout", "WiFi", "Developer Options", "< Back"]
dev_options_menu_items = ["Debug Mode: OFF", "< Back"]
games_menu_items    = ["Party Mode", "Snake", "Pong", "Drawing", "< Back"]
power_menu_items    = ["Sleep", "Reboot", "Shutdown", "< Back"]

current_menu_items = main_menu_items

# Click detection
last_click_time       = 0
click_start_time      = 0
movement_during_click = 0
MOVEMENT_THRESHOLD    = 3
SCROLL_SENSITIVITY    = 5

# Screen state
screen_on          = True
screen_timeout     = 60      # seconds; overwritten by settings on startup
last_activity_time = time.time()
sleeping           = False
sleep_enter_time   = 0.0

# Volume / brightness / sensitivity state
current_volume       = 50
current_brightness   = 100
current_sensitivity  = 5   # Range 1-10; SCROLL_SENSITIVITY = 21 - current_sensitivity * 2

# Party mode state
party_active = False
party_speed  = 30       # steps/sec, range 10-100
party_hue    = 0.0
party_lock   = threading.Lock()
party_thread = None     # Keep reference so we can join it

# Drawing game state
drawing_canvas         = None
drawing_draw_ctx       = None
drawing_mode           = True   # True = draw mode, False = move mode
drawing_hue            = 0.0
drawing_cursor_x       = 120
drawing_cursor_y       = 140
drawing_dirty          = False
drawing_dx_acc         = 0
drawing_dy_acc         = 0
drawing_exit_requested = False

# Snake game state
snake_body       = []
snake_direction  = (1, 0)   # (dx, dy) — starts moving right
snake_food       = (0, 0)
snake_alive      = True
snake_score      = 0
snake_speed      = 6        # moves per second
snake_last_move  = 0.0
snake_paused     = False

# Power confirmation state
power_confirm_action = None  # "shutdown" or "reboot"

# Voice recording / STT state
whisper_model        = None   # None = unavailable, "tiny" = model name
whisper_cpp_bin      = None   # Path to whisper-cli binary
whisper_cpp_model    = None   # Path to ggml-tiny.bin model
hat_button_held      = False
hat_button_press_time = 0.0
pre_record_state     = None

# Debug mode
debug = False

# OTA / About screen state
ota_status         = None   # None | "up_to_date" | "update_available"
ota_status_changed = False  # Set True by background thread; cleared by main loop

# Battery state
_battery_level = None
_battery_lock  = threading.Lock()


def get_battery_level():
    with _battery_lock:
        return _battery_level

import threading
from PIL import Image, ImageDraw


class AppState:
    MAIN          = "main"
    MAIN_MENU     = "main_menu"
    SETTINGS_MENU = "settings_menu"
    GAMES_MENU    = "games_menu"
    POWER_MENU    = "power_menu"
    PARTY_MODE    = "party_mode"
    OTA_CONFIRM   = "ota_confirm"
    OTA_RESULT    = "ota_result"
    VOLUME                = "volume"
    BRIGHTNESS            = "brightness"
    TRACKBALL_SENSITIVITY = "trackball_sensitivity"
    DRAWING               = "drawing"


# Canvas
img  = Image.new('RGB', (240, 280), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

# App state
current_state      = AppState.MAIN
menu_index         = 0
prev_menu_index    = -1
scroll_accumulator = 0

# Menu item lists
main_menu_items     = ["Status", "Settings", "Games", "Power"]
settings_menu_items = ["Software Update", "Volume", "Brightness", "Trackball Sensitivity", "WiFi", "< Back"]
games_menu_items    = ["Party Mode", "Snake", "Pong", "Drawing", "< Back"]
power_menu_items    = ["Sleep", "Reboot", "Shutdown", "< Back"]

current_menu_items = main_menu_items

# Click detection
last_click_time       = 0
click_start_time      = 0
movement_during_click = 0
MOVEMENT_THRESHOLD    = 3
SCROLL_SENSITIVITY    = 5

# Volume / brightness / sensitivity state
current_volume       = 50
current_brightness   = 100
current_sensitivity  = 5   # Range 1-10; SCROLL_SENSITIVITY = 11 - current_sensitivity

# Party mode state
party_active = False
party_speed  = 30       # steps/sec, range 10-100
party_hue    = 0.0
party_lock   = threading.Lock()
party_thread = None     # Keep reference so we can join it

# Drawing game state
drawing_canvas         = None   # PIL Image (the persistent drawing canvas)
drawing_draw_ctx       = None   # PIL ImageDraw for drawing_canvas
drawing_mode           = True   # True = draw mode, False = move mode
drawing_hue            = 0.0    # Current HSV hue for rainbow color cycling
drawing_cursor_x       = 120    # Cursor X position (0-239)
drawing_cursor_y       = 140    # Cursor Y position (0-279)
drawing_dirty          = False  # True when display needs to be refreshed
drawing_dx_acc         = 0      # Horizontal trackball accumulator
drawing_dy_acc         = 0      # Vertical trackball accumulator
drawing_exit_requested = False  # Set by HAT button to signal exit

# Battery state
_battery_level = None
_battery_lock  = threading.Lock()


def get_battery_level():
    with _battery_lock:
        return _battery_level

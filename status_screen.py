#!/usr/bin/env python3
import time
import sys
import os
import subprocess
import threading
import numpy as np
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Import drivers
sys.path.append(os.path.expanduser("~/Whisplay/Driver"))
from WhisPlay import WhisPlayBoard
from trackball import TrackBall

print("Initializing board...")
board = WhisPlayBoard()
board.set_backlight(100)
print("Board initialized")

# Trackball init - non-fatal if missing
try:
    trackball = TrackBall(interrupt_pin=None)
    trackball_available = True
    print("Trackball initialized")
except Exception as e:
    trackball = None
    trackball_available = False
    print(f"Trackball not found, continuing without it: {e}")

print("Hardware initialized")

# Create blank image
img = Image.new('RGB', (240, 280), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

# Margins
MARGIN_LEFT = 15
MARGIN_TOP = 15
MARGIN_BOTTOM = 255

# State
class AppState:
    MAIN = "main"
    MAIN_MENU = "main_menu"
    SETTINGS_MENU = "settings_menu"
    GAMES_MENU = "games_menu"
    POWER_MENU = "power_menu"

current_state = AppState.MAIN
menu_index = 0
prev_menu_index = -1
scroll_accumulator = 0

# Menu definitions
main_menu_items = ["Status", "Settings", "Games", "Power"]
settings_menu_items = ["Volume", "Brightness", "WiFi", "< Back"]
games_menu_items = ["Snake", "Pong", "Drawing", "< Back"]
power_menu_items = ["Sleep", "Reboot", "Shutdown", "< Back"]

current_menu_items = main_menu_items

# Click detection
last_click_time = 0
click_start_time = 0
movement_during_click = 0
MOVEMENT_THRESHOLD = 3
SCROLL_SENSITIVITY = 5

# Battery polling - background thread so it never blocks the main loop
_battery_level = None
_battery_lock = threading.Lock()

def _battery_poll_thread():
    global _battery_level
    while True:
        try:
            result = subprocess.run(
                ['bash', '-c', 'echo "get battery" | nc -q 0 127.0.0.1 8423'],
                capture_output=True, text=True, timeout=2
            )
            output = result.stdout.strip()
            if "battery:" in output:
                val = int(float(output.split(":")[-1].strip()))
                with _battery_lock:
                    _battery_level = val
        except Exception:
            pass
        time.sleep(30)

_battery_thread = threading.Thread(target=_battery_poll_thread, daemon=True)
_battery_thread.start()

def get_battery_level():
    with _battery_lock:
        return _battery_level


def set_trackball_color(r, g, b, w=0):
    """Set trackball RGB - safe no-op if trackball not available"""
    if trackball_available:
        try:
            trackball.set_rgbw(r, g, b, w)
        except Exception:
            pass


def image_to_rgb565(img):
    """Vectorized RGB565 conversion using numpy"""
    arr = np.array(img, dtype=np.uint16)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    result = np.empty(240 * 280 * 2, dtype=np.uint8)
    result[0::2] = (rgb565 >> 8).astype(np.uint8).flatten()
    result[1::2] = (rgb565 & 0xFF).astype(np.uint8).flatten()

    return result


def display_image():
    rotated = img.rotate(180)
    board.draw_image(0, 0, 240, 280, image_to_rgb565(rotated))


def draw_main_screen():
    draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))

    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%b %d, %Y")

    battery = get_battery_level()
    if battery is not None:
        battery_str = f"Battery: {battery}%"
        battery_color = (0, 255, 0) if battery > 50 else (255, 255, 0) if battery > 20 else (255, 0, 0)
    else:
        battery_str = "Battery: --"
        battery_color = (100, 100, 100)

    draw.text((MARGIN_LEFT, MARGIN_TOP), "READY", fill=(0, 255, 0))
    draw.text((MARGIN_LEFT, 50), time_str, fill=(255, 255, 255))
    draw.text((MARGIN_LEFT, 80), date_str, fill=(200, 200, 200))
    draw.text((MARGIN_LEFT, MARGIN_BOTTOM), battery_str, fill=battery_color)

    if trackball_available:
        draw.text((MARGIN_LEFT, 230), "Click for menu", fill=(100, 100, 100))
    else:
        draw.text((MARGIN_LEFT, 230), "No trackball", fill=(150, 50, 50))

    display_image()


def draw_menu_full(title):
    draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    draw.text((MARGIN_LEFT, MARGIN_TOP), title, fill=(255, 200, 0))

    for i, item in enumerate(current_menu_items):
        y_pos = 50 + (i * 30)
        if i == menu_index:
            draw.rectangle((MARGIN_LEFT - 5, y_pos - 2, 230, y_pos + 18), fill=(50, 50, 100))
            draw.text((MARGIN_LEFT, y_pos), f"> {item}", fill=(255, 255, 0))
        else:
            draw.text((MARGIN_LEFT + 10, y_pos), item, fill=(200, 200, 200))

    draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click to select", fill=(100, 100, 100))
    display_image()


def enter_submenu(new_state, items, title):
    global current_state, current_menu_items, menu_index, prev_menu_index
    current_state = new_state
    current_menu_items = items
    menu_index = 0
    prev_menu_index = -1
    draw_menu_full(title)


def get_menu_title():
    titles = {
        AppState.MAIN_MENU: "Menu",
        AppState.SETTINGS_MENU: "Settings",
        AppState.GAMES_MENU: "Games",
        AppState.POWER_MENU: "Power"
    }
    return titles.get(current_state, "Menu")


def handle_menu_selection():
    global current_state
    selected = current_menu_items[menu_index]
    print(f"Selected: {selected}")

    if current_state == AppState.MAIN_MENU:
        if selected == "Status":
            current_state = AppState.MAIN
            set_trackball_color(0, 255, 0)
            time.sleep(0.1)
            set_trackball_color(0, 0, 0)
            draw_main_screen()
        elif selected == "Settings":
            enter_submenu(AppState.SETTINGS_MENU, settings_menu_items, "Settings")
        elif selected == "Games":
            enter_submenu(AppState.GAMES_MENU, games_menu_items, "Games")
        elif selected == "Power":
            enter_submenu(AppState.POWER_MENU, power_menu_items, "Power")

    elif current_state == AppState.SETTINGS_MENU:
        if selected == "< Back":
            enter_submenu(AppState.MAIN_MENU, main_menu_items, "Menu")
        else:
            set_trackball_color(255, 0, 255)
            time.sleep(0.15)
            set_trackball_color(20, 20, 20)

    elif current_state == AppState.GAMES_MENU:
        if selected == "< Back":
            enter_submenu(AppState.MAIN_MENU, main_menu_items, "Menu")
        else:
            set_trackball_color(0, 0, 255)
            time.sleep(0.15)
            set_trackball_color(20, 20, 20)

    elif current_state == AppState.POWER_MENU:
        if selected == "< Back":
            enter_submenu(AppState.MAIN_MENU, main_menu_items, "Menu")
        else:
            set_trackball_color(255, 0, 0)
            time.sleep(0.15)
            set_trackball_color(20, 20, 20)


board.on_button_press(lambda: print("Recording mode TODO"))

try:
    print("Starting main loop...")
    draw_main_screen()
    last_second = int(time.time())
    button_was_down = False

    while True:
        # Trackball input - only if available
        if trackball_available:
            try:
                up, down, left, right, switch, state = trackball.read()
            except Exception as e:
                print(f"Trackball read error: {e}")
                up = down = left = right = switch = state = 0

            # Button state tracking
            if switch and not button_was_down:
                button_was_down = True
                click_start_time = time.time()
                movement_during_click = 0

            elif not switch and button_was_down:
                button_was_down = False
                click_duration = time.time() - click_start_time

                if (click_duration < 0.5 and
                    movement_during_click < MOVEMENT_THRESHOLD and
                    time.time() - last_click_time > 0.3):

                    last_click_time = time.time()

                    if current_state == AppState.MAIN:
                        current_state = AppState.MAIN_MENU
                        current_menu_items = main_menu_items
                        menu_index = 0
                        prev_menu_index = -1
                        set_trackball_color(20, 20, 20)
                        draw_menu_full("Menu")
                    else:
                        handle_menu_selection()

            if button_was_down:
                movement_during_click += abs(up) + abs(down) + abs(left) + abs(right)

            # Menu navigation
            if current_state != AppState.MAIN and not button_was_down:
                net_movement = down - up

                if abs(net_movement) > 0:
                    scroll_accumulator += net_movement

                    if abs(scroll_accumulator) >= SCROLL_SENSITIVITY:
                        if scroll_accumulator > 0:
                            menu_index = (menu_index + 1) % len(current_menu_items)
                        else:
                            menu_index = (menu_index - 1) % len(current_menu_items)

                        draw_menu_full(get_menu_title())
                        scroll_accumulator = 0

        # Update time on main screen once per second
        if current_state == AppState.MAIN:
            current_second = int(time.time())
            if current_second != last_second:
                last_second = current_second
                draw_main_screen()

        time.sleep(0.008)  # ~125Hz poll rate

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    board.cleanup()
    set_trackball_color(0, 0, 0)
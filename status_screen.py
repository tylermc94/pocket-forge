#!/usr/bin/env python3
import time
import sys
import os
import subprocess
import threading
import colorsys
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

# Fonts
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_TITLE = ImageFont.truetype(FONT_PATH, 20)   # Titles
FONT_BODY  = ImageFont.truetype(FONT_PATH, 16)   # Body text
FONT_SMALL = ImageFont.truetype(FONT_PATH, 13)   # Hints/footer

# Margins
MARGIN_LEFT   = 15
MARGIN_TOP    = 15
MARGIN_BOTTOM = 255

# State
class AppState:
    MAIN         = "main"
    MAIN_MENU    = "main_menu"
    SETTINGS_MENU = "settings_menu"
    GAMES_MENU   = "games_menu"
    POWER_MENU   = "power_menu"
    PARTY_MODE   = "party_mode"
    OTA_CONFIRM  = "ota_confirm"
    OTA_RESULT   = "ota_result"

current_state     = AppState.MAIN
menu_index        = 0
prev_menu_index   = -1
scroll_accumulator = 0

# Menu definitions
main_menu_items     = ["Status", "Settings", "Games", "Power"]
settings_menu_items = ["Software Update", "Volume", "Brightness", "WiFi", "< Back"]
games_menu_items    = ["Party Mode", "Snake", "Pong", "Drawing", "< Back"]
power_menu_items    = ["Sleep", "Reboot", "Shutdown", "< Back"]

current_menu_items = main_menu_items

# Click detection
last_click_time       = 0
click_start_time      = 0
movement_during_click = 0
MOVEMENT_THRESHOLD    = 3
SCROLL_SENSITIVITY    = 5

# Party mode state
party_active  = False
party_speed   = 30       # steps/sec, range 10-100
party_hue     = 0.0
party_lock    = threading.Lock()
party_thread  = None     # Keep reference so we can join it

# Battery polling
_battery_level = None
_battery_lock  = threading.Lock()

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


# ==================== Trackball LED ====================

def set_trackball_color(r, g, b, w=0):
    if trackball_available:
        try:
            trackball.set_rgbw(r, g, b, w)
        except Exception:
            pass


def _party_thread_func():
    global party_hue
    while True:
        with party_lock:
            active = party_active
            speed  = party_speed
            hue    = party_hue

        if not active:
            set_trackball_color(0, 0, 0)
            break

        hue = (hue + 0.01) % 1.0
        with party_lock:
            party_hue = hue

        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        set_trackball_color(int(r * 255), int(g * 255), int(b * 255))
        draw_party_screen(r, g, b)

        time.sleep(1.0 / speed)


def start_party_mode():
    global party_active, party_hue, party_thread
    with party_lock:
        party_active = True
        party_hue    = 0.0
    party_thread = threading.Thread(target=_party_thread_func, daemon=True)
    party_thread.start()


def stop_party_mode():
    """Signal thread to stop and wait for it to finish before returning"""
    global party_active, party_thread
    with party_lock:
        party_active = False
    if party_thread is not None:
        party_thread.join(timeout=1.0)
        party_thread = None
    set_trackball_color(0, 0, 0)


# ==================== Display ====================

def image_to_rgb565(source):
    arr = np.array(source, dtype=np.uint16)
    r   = arr[:, :, 0]
    g   = arr[:, :, 1]
    b   = arr[:, :, 2]

    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    result       = np.empty(240 * 280 * 2, dtype=np.uint8)
    result[0::2] = (rgb565 >> 8).astype(np.uint8).flatten()
    result[1::2] = (rgb565 & 0xFF).astype(np.uint8).flatten()
    return result


def display_image():
    rotated = img.rotate(180)
    board.draw_image(0, 0, 240, 280, image_to_rgb565(rotated))


def draw_main_screen():
    draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))

    now      = datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%b %d, %Y")

    battery = get_battery_level()
    if battery is not None:
        battery_str   = f"Battery: {battery}%"
        battery_color = (0, 255, 0) if battery > 50 else (255, 255, 0) if battery > 20 else (255, 0, 0)
    else:
        battery_str   = "Battery: --"
        battery_color = (100, 100, 100)

    draw.text((MARGIN_LEFT, MARGIN_TOP), "READY",      font=FONT_TITLE, fill=(0, 255, 0))
    draw.text((MARGIN_LEFT, 50),         time_str,     font=FONT_BODY,  fill=(255, 255, 255))
    draw.text((MARGIN_LEFT, 75),         date_str,     font=FONT_BODY,  fill=(200, 200, 200))
    draw.text((MARGIN_LEFT, MARGIN_BOTTOM), battery_str, font=FONT_SMALL, fill=battery_color)

    hint = "Click for menu" if trackball_available else "No trackball"
    hint_color = (100, 100, 100) if trackball_available else (150, 50, 50)
    draw.text((MARGIN_LEFT, 230), hint, font=FONT_SMALL, fill=hint_color)

    display_image()


def draw_menu_full(title):
    draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    draw.text((MARGIN_LEFT, MARGIN_TOP), title, font=FONT_TITLE, fill=(255, 200, 0))

    for i, item in enumerate(current_menu_items):
        y_pos = 48 + (i * 32)
        if i == menu_index:
            draw.rectangle((MARGIN_LEFT - 5, y_pos - 2, 230, y_pos + 20), fill=(50, 50, 100))
            draw.text((MARGIN_LEFT, y_pos), f"> {item}", font=FONT_BODY, fill=(255, 255, 0))
        else:
            draw.text((MARGIN_LEFT + 10, y_pos), item, font=FONT_BODY, fill=(200, 200, 200))

    draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click to select", font=FONT_SMALL, fill=(100, 100, 100))
    display_image()


def draw_party_screen(r, g, b):
    color = (int(r * 255), int(g * 255), int(b * 255))
    draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    draw.text((MARGIN_LEFT, 80),  "PARTY MODE", font=FONT_TITLE, fill=color)

    with party_lock:
        speed = party_speed
    speed_pct = int((speed - 10) / 90 * 100)
    draw.text((MARGIN_LEFT, 120), f"Speed: {speed_pct}%",       font=FONT_BODY,  fill=(200, 200, 200))
    draw.text((MARGIN_LEFT, 150), "Scroll to change speed",     font=FONT_SMALL, fill=(100, 100, 100))
    draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click to exit",    font=FONT_SMALL, fill=(100, 100, 100))
    display_image()


def draw_ota_confirm():
    draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    draw.text((MARGIN_LEFT, MARGIN_TOP), "Software Update", font=FONT_TITLE, fill=(255, 200, 0))
    draw.text((MARGIN_LEFT, 70),  "Update available!",      font=FONT_BODY,  fill=(255, 255, 255))
    draw.text((MARGIN_LEFT, 100), "Apply update?",          font=FONT_BODY,  fill=(200, 200, 200))

    if menu_index == 0:
        draw.rectangle((MARGIN_LEFT - 5, 138, 120, 160), fill=(50, 50, 100))
        draw.text((MARGIN_LEFT, 140), "> Yes", font=FONT_BODY, fill=(255, 255, 0))
        draw.text((MARGIN_LEFT + 10, 172), "No", font=FONT_BODY, fill=(200, 200, 200))
    else:
        draw.text((MARGIN_LEFT + 10, 140), "Yes", font=FONT_BODY, fill=(200, 200, 200))
        draw.rectangle((MARGIN_LEFT - 5, 170, 120, 192), fill=(50, 50, 100))
        draw.text((MARGIN_LEFT, 172), "> No",  font=FONT_BODY, fill=(255, 255, 0))

    display_image()


def draw_ota_result(message, color=(255, 255, 255), pause=0):
    """Draw OTA result screen. Pass pause > 0 to hold the screen briefly."""
    draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    draw.text((MARGIN_LEFT, MARGIN_TOP), "Software Update", font=FONT_TITLE, fill=(255, 200, 0))

    # Simple word wrap
    words = message.split()
    line  = ""
    y     = 70
    for word in words:
        test = f"{line} {word}".strip()
        if len(test) > 20:
            draw.text((MARGIN_LEFT, y), line, font=FONT_BODY, fill=color)
            y    += 28
            line  = word
        else:
            line = test
    if line:
        draw.text((MARGIN_LEFT, y), line, font=FONT_BODY, fill=color)

    draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click to go back", font=FONT_SMALL, fill=(100, 100, 100))
    display_image()

    if pause > 0:
        time.sleep(pause)


# ==================== OTA Update ====================

def check_for_update():
    """Returns True if update available, False if up to date, None on error"""
    try:
        subprocess.run(
            ['git', 'fetch'],
            cwd='/home/admin/pocket-forge',
            capture_output=True, timeout=15
        )
        local = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd='/home/admin/pocket-forge',
            capture_output=True, text=True
        ).stdout.strip()
        remote = subprocess.run(
            ['git', 'rev-parse', 'origin/main'],
            cwd='/home/admin/pocket-forge',
            capture_output=True, text=True
        ).stdout.strip()
        return local != remote
    except Exception as e:
        print(f"OTA check error: {e}")
        return None


def apply_update():
    """Runs git pull then restarts service. Returns (success, message)"""
    try:
        result = subprocess.run(
            ['git', 'pull'],
            cwd='/home/admin/pocket-forge',
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return False, f"Pull failed: {result.stderr.strip()}"
        subprocess.Popen(['sudo', 'systemctl', 'restart', 'pocket-forge'])
        return True, "Restarting..."
    except Exception as e:
        return False, f"Error: {str(e)}"


def handle_ota():
    global current_state, menu_index

    draw_ota_result("Checking for updates...", color=(200, 200, 200))

    has_update = check_for_update()

    if has_update is None:
        current_state = AppState.OTA_RESULT
        draw_ota_result("Could not reach server. Check WiFi.", color=(255, 100, 100), pause=2)
    elif not has_update:
        current_state = AppState.OTA_RESULT
        draw_ota_result("Already up to date!", color=(0, 255, 0), pause=2)
    else:
        current_state = AppState.OTA_CONFIRM
        menu_index    = 0
        draw_ota_confirm()


# ==================== Menu Logic ====================

def enter_submenu(new_state, items, title):
    global current_state, current_menu_items, menu_index, prev_menu_index
    current_state      = new_state
    current_menu_items = items
    menu_index         = 0
    prev_menu_index    = -1
    draw_menu_full(title)


def get_menu_title():
    titles = {
        AppState.MAIN_MENU:     "Menu",
        AppState.SETTINGS_MENU: "Settings",
        AppState.GAMES_MENU:    "Games",
        AppState.POWER_MENU:    "Power"
    }
    return titles.get(current_state, "Menu")


def handle_menu_selection():
    global current_state, party_speed

    selected = current_menu_items[menu_index]
    print(f"Selected: {selected}")

    if current_state == AppState.MAIN_MENU:
        if selected == "Status":
            current_state = AppState.MAIN
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
        elif selected == "Software Update":
            handle_ota()
        else:
            set_trackball_color(255, 0, 255)
            time.sleep(0.15)
            set_trackball_color(0, 0, 0)

    elif current_state == AppState.GAMES_MENU:
        if selected == "< Back":
            enter_submenu(AppState.MAIN_MENU, main_menu_items, "Menu")
        elif selected == "Party Mode":
            current_state = AppState.PARTY_MODE
            party_speed   = 30
            start_party_mode()
        else:
            set_trackball_color(0, 0, 255)
            time.sleep(0.15)
            set_trackball_color(0, 0, 0)

    elif current_state == AppState.POWER_MENU:
        if selected == "< Back":
            enter_submenu(AppState.MAIN_MENU, main_menu_items, "Menu")
        else:
            set_trackball_color(255, 0, 0)
            time.sleep(0.15)
            set_trackball_color(0, 0, 0)

    elif current_state == AppState.OTA_CONFIRM:
        if menu_index == 0:  # Yes
            draw_ota_result("Applying update...", color=(200, 200, 200))
            success, message = apply_update()
            if not success:
                current_state = AppState.OTA_RESULT
                draw_ota_result(message, color=(255, 100, 100))
        else:  # No
            enter_submenu(AppState.SETTINGS_MENU, settings_menu_items, "Settings")

    elif current_state == AppState.OTA_RESULT:
        enter_submenu(AppState.SETTINGS_MENU, settings_menu_items, "Settings")


# ==================== Main Loop ====================

board.on_button_press(lambda: print("Recording mode TODO"))

try:
    print("Starting main loop...")
    draw_main_screen()
    last_second   = int(time.time())
    button_was_down = False

    while True:
        if trackball_available:
            try:
                up, down, left, right, switch, state = trackball.read()
            except Exception as e:
                print(f"Trackball read error: {e}")
                up = down = left = right = switch = state = 0

            # Button tracking
            if switch and not button_was_down:
                button_was_down       = True
                click_start_time      = time.time()
                movement_during_click = 0

            elif not switch and button_was_down:
                button_was_down = False
                click_duration  = time.time() - click_start_time

                if (click_duration < 0.5 and
                        movement_during_click < MOVEMENT_THRESHOLD and
                        time.time() - last_click_time > 0.3):

                    last_click_time = time.time()

                    if current_state == AppState.PARTY_MODE:
                        # Stop thread first, then redraw menu
                        stop_party_mode()
                        enter_submenu(AppState.GAMES_MENU, games_menu_items, "Games")

                    elif current_state == AppState.MAIN:
                        current_state      = AppState.MAIN_MENU
                        current_menu_items = main_menu_items
                        menu_index         = 0
                        prev_menu_index    = -1
                        draw_menu_full("Menu")

                    else:
                        handle_menu_selection()

            if button_was_down:
                movement_during_click += abs(up) + abs(down) + abs(left) + abs(right)

            # Scroll handling
            net_movement = down - up
            if abs(net_movement) > 0:
                if current_state == AppState.PARTY_MODE:
                    with party_lock:
                        party_speed = max(10, min(100, party_speed + (2 if net_movement > 0 else -2)))

                elif current_state not in (AppState.MAIN, AppState.OTA_RESULT):
                    scroll_accumulator += net_movement
                    if abs(scroll_accumulator) >= SCROLL_SENSITIVITY:
                        item_count = 2 if current_state == AppState.OTA_CONFIRM else len(current_menu_items)

                        if scroll_accumulator > 0:
                            menu_index = (menu_index + 1) % item_count
                        else:
                            menu_index = (menu_index - 1) % item_count

                        if current_state == AppState.OTA_CONFIRM:
                            draw_ota_confirm()
                        else:
                            draw_menu_full(get_menu_title())
                        scroll_accumulator = 0

        # Main screen clock update
        if current_state == AppState.MAIN:
            current_second = int(time.time())
            if current_second != last_second:
                last_second = current_second
                draw_main_screen()

        time.sleep(0.008)

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    stop_party_mode()
    board.cleanup()
    set_trackball_color(0, 0, 0)
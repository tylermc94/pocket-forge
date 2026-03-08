import time
from datetime import datetime

import numpy as np
from PIL import ImageFont

import state
import hardware

# Fonts
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_TITLE = ImageFont.truetype(FONT_PATH, 20)
FONT_BODY  = ImageFont.truetype(FONT_PATH, 16)
FONT_SMALL = ImageFont.truetype(FONT_PATH, 13)

# Layout constants
MARGIN_LEFT   = 15
MARGIN_TOP    = 15
MARGIN_BOTTOM = 255


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
    rotated = state.img.rotate(180)
    hardware.board.draw_image(0, 0, 240, 280, image_to_rgb565(rotated))


def draw_blank_screen():
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    display_image()


def draw_main_screen():
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))

    now      = datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%b %d, %Y")

    battery = state.get_battery_level()
    if battery is not None:
        battery_str   = f"Battery: {battery}%"
        battery_color = (0, 255, 0) if battery > 50 else (255, 255, 0) if battery > 20 else (255, 0, 0)
    else:
        battery_str   = "Battery: --"
        battery_color = (100, 100, 100)

    state.draw.text((MARGIN_LEFT, MARGIN_TOP), "READY",      font=FONT_TITLE, fill=(0, 255, 0))
    state.draw.text((MARGIN_LEFT, 50),         time_str,     font=FONT_BODY,  fill=(255, 255, 255))
    state.draw.text((MARGIN_LEFT, 75),         date_str,     font=FONT_BODY,  fill=(200, 200, 200))
    state.draw.text((MARGIN_LEFT, MARGIN_BOTTOM), battery_str, font=FONT_SMALL, fill=battery_color)

    hint = "Click for menu" if hardware.trackball_available else "No trackball"
    hint_color = (100, 100, 100) if hardware.trackball_available else (150, 50, 50)
    state.draw.text((MARGIN_LEFT, 230), hint, font=FONT_SMALL, fill=hint_color)

    display_image()


def draw_menu_full(title):
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    state.draw.text((MARGIN_LEFT, MARGIN_TOP), title, font=FONT_TITLE, fill=(255, 200, 0))

    for i, item in enumerate(state.current_menu_items):
        y_pos = 48 + (i * 32)
        if i == state.menu_index:
            state.draw.rectangle((MARGIN_LEFT - 5, y_pos - 2, 230, y_pos + 20), fill=(50, 50, 100))
            state.draw.text((MARGIN_LEFT, y_pos), f"> {item}", font=FONT_BODY, fill=(255, 255, 0))
        else:
            state.draw.text((MARGIN_LEFT + 10, y_pos), item, font=FONT_BODY, fill=(200, 200, 200))

    state.draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click to select", font=FONT_SMALL, fill=(100, 100, 100))
    display_image()


def draw_slider_screen(title, value, unit):
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    state.draw.text((MARGIN_LEFT, MARGIN_TOP), title, font=FONT_TITLE, fill=(255, 200, 0))
    state.draw.text((MARGIN_LEFT, 60), f"{value}{unit}", font=FONT_BODY, fill=(255, 255, 255))

    # Bar background and fill
    BAR_LEFT, BAR_TOP, BAR_RIGHT, BAR_BOTTOM = MARGIN_LEFT, 95, 225, 115
    state.draw.rectangle((BAR_LEFT, BAR_TOP, BAR_RIGHT, BAR_BOTTOM), fill=(50, 50, 50))
    filled = int((BAR_RIGHT - BAR_LEFT) * value / 100)
    if filled > 0:
        state.draw.rectangle((BAR_LEFT, BAR_TOP, BAR_LEFT + filled, BAR_BOTTOM), fill=(0, 200, 100))

    state.draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click to confirm", font=FONT_SMALL, fill=(100, 100, 100))
    display_image()


def draw_sensitivity_screen(value):
    """Trackball sensitivity slider, value 1-10."""
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    state.draw.text((MARGIN_LEFT, MARGIN_TOP), "Sensitivity", font=FONT_TITLE, fill=(255, 200, 0))
    state.draw.text((MARGIN_LEFT, 60), f"{value * 10}%", font=FONT_BODY, fill=(255, 255, 255))

    BAR_LEFT, BAR_TOP, BAR_RIGHT, BAR_BOTTOM = MARGIN_LEFT, 95, 225, 115
    state.draw.rectangle((BAR_LEFT, BAR_TOP, BAR_RIGHT, BAR_BOTTOM), fill=(50, 50, 50))
    filled = int((BAR_RIGHT - BAR_LEFT) * value / 10)
    if filled > 0:
        state.draw.rectangle((BAR_LEFT, BAR_TOP, BAR_LEFT + filled, BAR_BOTTOM), fill=(0, 200, 100))

    state.draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click to confirm", font=FONT_SMALL, fill=(100, 100, 100))
    display_image()


def draw_party_screen(r, g, b):
    color = (int(r * 255), int(g * 255), int(b * 255))
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    state.draw.text((MARGIN_LEFT, 80),  "PARTY MODE", font=FONT_TITLE, fill=color)

    with state.party_lock:
        speed = state.party_speed
    speed_pct = int((speed - 10) / 90 * 100)
    state.draw.text((MARGIN_LEFT, 120), f"Speed: {speed_pct}%",    font=FONT_BODY,  fill=(200, 200, 200))
    state.draw.text((MARGIN_LEFT, 150), "Scroll to change speed",  font=FONT_SMALL, fill=(100, 100, 100))
    state.draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click to exit", font=FONT_SMALL, fill=(100, 100, 100))
    display_image()


def draw_ota_confirm():
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    state.draw.text((MARGIN_LEFT, MARGIN_TOP), "Software Update", font=FONT_TITLE, fill=(255, 200, 0))
    state.draw.text((MARGIN_LEFT, 70),  "Update available!",      font=FONT_BODY,  fill=(255, 255, 255))
    state.draw.text((MARGIN_LEFT, 100), "Apply update?",          font=FONT_BODY,  fill=(200, 200, 200))

    if state.menu_index == 0:
        state.draw.rectangle((MARGIN_LEFT - 5, 138, 120, 160), fill=(50, 50, 100))
        state.draw.text((MARGIN_LEFT, 140), "> Yes", font=FONT_BODY, fill=(255, 255, 0))
        state.draw.text((MARGIN_LEFT + 10, 172), "No", font=FONT_BODY, fill=(200, 200, 200))
    else:
        state.draw.text((MARGIN_LEFT + 10, 140), "Yes", font=FONT_BODY, fill=(200, 200, 200))
        state.draw.rectangle((MARGIN_LEFT - 5, 170, 120, 192), fill=(50, 50, 100))
        state.draw.text((MARGIN_LEFT, 172), "> No",  font=FONT_BODY, fill=(255, 255, 0))

    display_image()


def draw_ota_result(message, color=(255, 255, 255), pause=0):
    """Draw OTA result screen. Pass pause > 0 to hold the screen briefly."""
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    state.draw.text((MARGIN_LEFT, MARGIN_TOP), "Software Update", font=FONT_TITLE, fill=(255, 200, 0))

    # Simple word wrap
    words = message.split()
    line  = ""
    y     = 70
    for word in words:
        test = f"{line} {word}".strip()
        if len(test) > 20:
            state.draw.text((MARGIN_LEFT, y), line, font=FONT_BODY, fill=color)
            y    += 28
            line  = word
        else:
            line = test
    if line:
        state.draw.text((MARGIN_LEFT, y), line, font=FONT_BODY, fill=color)

    state.draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click to go back", font=FONT_SMALL, fill=(100, 100, 100))
    display_image()

    if pause > 0:
        time.sleep(pause)


def draw_about_checking():
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    state.draw.text((MARGIN_LEFT, MARGIN_TOP), "About", font=FONT_TITLE, fill=(255, 200, 0))
    state.draw.text((MARGIN_LEFT, 70), "Checking for updates...", font=FONT_SMALL, fill=(200, 200, 200))
    display_image()


def draw_about_screen(has_update):
    """Draw About screen. has_update: True=update available, False=up to date, None=error."""
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    state.draw.text((MARGIN_LEFT, MARGIN_TOP), "About", font=FONT_TITLE, fill=(255, 200, 0))
    state.draw.text((MARGIN_LEFT, 55), "Pocket Forge", font=FONT_BODY, fill=(255, 255, 255))

    if has_update is True:
        state.draw.rectangle((MARGIN_LEFT - 5, 98, 230, 120), fill=(50, 50, 100))
        state.draw.text((MARGIN_LEFT, 100), "> Update available", font=FONT_BODY, fill=(255, 255, 0))
        state.draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click to update", font=FONT_SMALL, fill=(100, 100, 100))
    elif has_update is False:
        state.draw.text((MARGIN_LEFT, 100), "Software up to date", font=FONT_BODY, fill=(0, 255, 0))
        state.draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click to go back", font=FONT_SMALL, fill=(100, 100, 100))
    else:
        state.draw.text((MARGIN_LEFT, 100), "Could not check", font=FONT_BODY, fill=(255, 100, 100))
        state.draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click to go back", font=FONT_SMALL, fill=(100, 100, 100))

    display_image()


def draw_power_confirm(action):
    """action: 'poweroff' or 'reboot'"""
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    label = "Power off?" if action == "poweroff" else "Restart?"
    state.draw.text((MARGIN_LEFT, MARGIN_TOP), label, font=FONT_TITLE, fill=(255, 200, 0))

    if state.menu_index == 0:
        state.draw.rectangle((MARGIN_LEFT - 5, 78, 120, 100), fill=(50, 50, 100))
        state.draw.text((MARGIN_LEFT, 80), "> Yes", font=FONT_BODY, fill=(255, 255, 0))
        state.draw.text((MARGIN_LEFT + 10, 112), "No", font=FONT_BODY, fill=(200, 200, 200))
    else:
        state.draw.text((MARGIN_LEFT + 10, 80), "Yes", font=FONT_BODY, fill=(200, 200, 200))
        state.draw.rectangle((MARGIN_LEFT - 5, 110, 120, 132), fill=(50, 50, 100))
        state.draw.text((MARGIN_LEFT, 112), "> No", font=FONT_BODY, fill=(255, 255, 0))

    display_image()


def draw_drawing_screen():
    """Draws the full drawing canvas from scratch."""
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))

    for (px, py) in state.drawing_pixels:
        state.draw.rectangle((px - 2, py - 2, px + 2, py + 2), fill=(255, 255, 255))

    # Cursor crosshair
    cx, cy = state.drawing_cursor_x, state.drawing_cursor_y
    state.draw.line((cx - 5, cy, cx + 5, cy), fill=(0, 200, 255), width=1)
    state.draw.line((cx, cy - 5, cx, cy + 5), fill=(0, 200, 255), width=1)

    state.draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click: Draw/Move  Hold: Exit",
                    font=FONT_SMALL, fill=(100, 100, 100))
    display_image()


def draw_snake_screen():
    """Draws the snake game frame."""
    CELL = 12
    BORDER = 4
    PLAY_W = 240 - BORDER * 2
    PLAY_H = 260 - BORDER * 2   # leave room at bottom for score
    COLS = PLAY_W // CELL
    ROWS = PLAY_H // CELL

    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    # Play field border
    state.draw.rectangle((BORDER - 1, BORDER - 1, BORDER + COLS * CELL, BORDER + ROWS * CELL),
                          outline=(60, 60, 60))

    # Snake body
    for i, (gx, gy) in enumerate(state.snake_body):
        px = BORDER + gx * CELL
        py = BORDER + gy * CELL
        color = (0, 220, 0) if i == 0 else (0, 160, 0)
        state.draw.rectangle((px + 1, py + 1, px + CELL - 2, py + CELL - 2), fill=color)

    # Food
    fx = BORDER + state.snake_food[0] * CELL + CELL // 2
    fy = BORDER + state.snake_food[1] * CELL + CELL // 2
    r  = CELL // 2 - 1
    state.draw.ellipse((fx - r, fy - r, fx + r, fy + r), fill=(255, 60, 60))

    # Score
    state.draw.text((MARGIN_LEFT, MARGIN_BOTTOM), f"Score: {state.snake_score}",
                    font=FONT_SMALL, fill=(200, 200, 200))

    if state.snake_paused:
        state.draw.text((80, 120), "PAUSED", font=FONT_BODY, fill=(255, 200, 0))
        state.draw.text((55, 145), "Click to resume", font=FONT_SMALL, fill=(150, 150, 150))

    display_image()


def draw_snake_dead_screen():
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    state.draw.text((MARGIN_LEFT, 80),  "GAME OVER",          font=FONT_TITLE, fill=(255, 60, 60))
    state.draw.text((MARGIN_LEFT, 120), f"Score: {state.snake_score}", font=FONT_BODY,  fill=(255, 255, 255))
    state.draw.text((MARGIN_LEFT, MARGIN_BOTTOM), "Hold to exit", font=FONT_SMALL, fill=(100, 100, 100))
    display_image()

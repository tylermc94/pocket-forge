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
    state.draw.text((MARGIN_LEFT, 55), f"{value}{unit}", font=FONT_BODY, fill=(255, 255, 255))

    # Vertical bar — fills from bottom (low) to top (high)
    BAR_LEFT, BAR_TOP, BAR_RIGHT, BAR_BOTTOM = 95, 85, 145, 240
    state.draw.rectangle((BAR_LEFT, BAR_TOP, BAR_RIGHT, BAR_BOTTOM), fill=(50, 50, 50))
    bar_height = BAR_BOTTOM - BAR_TOP
    filled = int(bar_height * value / 100)
    if filled > 0:
        state.draw.rectangle((BAR_LEFT, BAR_BOTTOM - filled, BAR_RIGHT, BAR_BOTTOM), fill=(0, 200, 100))

    # Min / max labels
    state.draw.text((BAR_RIGHT + 8, BAR_TOP),        "MAX", font=FONT_SMALL, fill=(150, 150, 150))
    state.draw.text((BAR_RIGHT + 8, BAR_BOTTOM - 14), "MIN", font=FONT_SMALL, fill=(150, 150, 150))

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


def draw_drawing_screen():
    """
    Render the drawing canvas with a cursor overlay and mode indicator,
    then push to the display.  The persistent canvas is kept in
    state.drawing_canvas; only a composite copy is sent to the screen so
    the cursor and UI chrome are never burned into the drawing itself.
    """
    if state.drawing_canvas is None:
        return

    from PIL import Image as _Image, ImageDraw as _ImageDraw

    # Work on a copy so the canvas stays clean
    composite  = state.drawing_canvas.copy()
    comp_draw  = _ImageDraw.Draw(composite)

    # --- Crosshair cursor (5 px arms, white with black halo) ---
    cx, cy = state.drawing_cursor_x, state.drawing_cursor_y
    hs = 5  # arm half-length

    # Black 3-px-wide outline first so cursor is visible on any background
    comp_draw.line([(cx - hs - 1, cy), (cx + hs + 1, cy)], fill=(0, 0, 0), width=3)
    comp_draw.line([(cx, cy - hs - 1), (cx, cy + hs + 1)], fill=(0, 0, 0), width=3)
    # White 1-px crosshair on top
    comp_draw.line([(cx - hs, cy), (cx + hs, cy)], fill=(255, 255, 255), width=1)
    comp_draw.line([(cx, cy - hs), (cx, cy + hs)], fill=(255, 255, 255), width=1)

    # --- Mode indicator (top-left corner) ---
    mode_text  = "Draw" if state.drawing_mode else "Move"
    mode_color = (255, 255, 0) if state.drawing_mode else (0, 200, 255)
    comp_draw.rectangle((2, 2, 48, 17), fill=(0, 0, 0))
    comp_draw.text((4, 3), mode_text, font=FONT_SMALL, fill=mode_color)

    # Push composite into state.img and send to hardware
    state.img.paste(composite)
    display_image()

    state.drawing_dirty = False


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

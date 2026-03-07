import subprocess
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


def draw_drawing_screen():
    """Composite the drawing canvas onto the display with a cursor and hint overlay."""
    from PIL import Image as _Image
    canvas = state.drawing_canvas if state.drawing_canvas is not None else _Image.new('RGB', (240, 280))
    composite = canvas.copy()
    from PIL import ImageDraw as _ImageDraw
    overlay = _ImageDraw.Draw(composite)
    x, y = state.drawing_cursor_x, state.drawing_cursor_y
    cursor_color = (255, 255, 0) if state.drawing_mode else (200, 200, 200)
    overlay.ellipse((x - 4, y - 4, x + 4, y + 4), outline=cursor_color)
    mode_label = "DRAW" if state.drawing_mode else "MOVE"
    overlay.text((MARGIN_LEFT, MARGIN_TOP), mode_label, font=FONT_SMALL, fill=cursor_color)
    overlay.text((MARGIN_LEFT, MARGIN_BOTTOM), "Click: toggle  Hold: clear", font=FONT_SMALL, fill=(80, 80, 80))
    rotated = composite.rotate(180)
    hardware.board.draw_image(0, 0, 240, 280, image_to_rgb565(rotated))


_ABOUT_DIVIDER_Y = 218
_ABOUT_STATUS_Y  = 236


def _get_commit_info():
    """Return (firmware_date, commit_msg) from the local git repo."""
    repo = '/home/admin/pocket-forge'
    try:
        firmware_date = subprocess.run(
            ['git', 'log', '-1', '--format=%cd', '--date=format:%b %d %Y'],
            cwd=repo, capture_output=True, text=True
        ).stdout.strip() or "Unknown"
    except Exception:
        firmware_date = "Unknown"

    try:
        msg = subprocess.run(
            ['git', 'log', '-1', '--format=%s'],
            cwd=repo, capture_output=True, text=True
        ).stdout.strip() or ""
        if len(msg) > 26:
            msg = msg[:25] + "\u2026"
    except Exception:
        msg = ""

    return firmware_date, msg


def _draw_about_status_area():
    """Repaint only the area below the divider. Does NOT call display_image()."""
    state.draw.rectangle((0, _ABOUT_DIVIDER_Y + 1, 240, 280), fill=(0, 0, 0))

    s = state.ota_status
    if s is None:
        state.draw.text(
            (MARGIN_LEFT, _ABOUT_STATUS_Y), "Checking\u2026",
            font=FONT_SMALL, fill=(130, 130, 130)
        )
    elif s == "up_to_date":
        state.draw.text(
            (MARGIN_LEFT, _ABOUT_STATUS_Y), "Up to date",
            font=FONT_BODY, fill=(200, 200, 200)
        )
    else:  # update_available
        state.draw.rectangle(
            (MARGIN_LEFT - 5, _ABOUT_STATUS_Y - 2, 235, _ABOUT_STATUS_Y + 22),
            fill=(50, 50, 100)
        )
        state.draw.text(
            (MARGIN_LEFT, _ABOUT_STATUS_Y), "> Update available",
            font=FONT_BODY, fill=(255, 255, 0)
        )


def draw_about_screen():
    state.draw.rectangle((0, 0, 240, 280), fill=(0, 0, 0))
    state.draw.text((MARGIN_LEFT, MARGIN_TOP), "About", font=FONT_TITLE, fill=(255, 200, 0))

    firmware_date, commit_msg = _get_commit_info()

    DIM  = (130, 130, 130)
    LITE = (200, 200, 200)

    state.draw.text((MARGIN_LEFT, 50),  "Device: Pocket Forge",       font=FONT_SMALL, fill=LITE)
    state.draw.text((MARGIN_LEFT, 68),  "Hardware:",                   font=FONT_SMALL, fill=DIM)
    state.draw.text((MARGIN_LEFT, 84),  "Pi Zero 2W / Whisplay HAT",  font=FONT_SMALL, fill=LITE)
    state.draw.text((MARGIN_LEFT, 100), "/ PiSugar 3",                font=FONT_SMALL, fill=LITE)
    state.draw.text((MARGIN_LEFT, 118), f"Firmware: {firmware_date}", font=FONT_SMALL, fill=LITE)
    state.draw.text((MARGIN_LEFT, 136), "Last update:",               font=FONT_SMALL, fill=DIM)
    state.draw.text((MARGIN_LEFT, 152), commit_msg,                   font=FONT_SMALL, fill=LITE)

    state.draw.line(
        (MARGIN_LEFT, _ABOUT_DIVIDER_Y, 225, _ABOUT_DIVIDER_Y),
        fill=(60, 60, 60), width=1
    )

    _draw_about_status_area()
    display_image()


def draw_about_status():
    """Update only the status line on the About screen and refresh the display."""
    _draw_about_status_area()
    display_image()

import time
import colorsys
import threading

import state
import hardware
import display


def _party_thread_func():
    last_draw = 0.0
    while True:
        with state.party_lock:
            active = state.party_active
            speed  = state.party_speed
            hue    = state.party_hue

        if not active:
            hardware.set_trackball_color(0, 0, 0)
            break

        hue = (hue + 0.01) % 1.0
        with state.party_lock:
            state.party_hue = hue

        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        hardware.set_trackball_color(int(r * 255), int(g * 255), int(b * 255))

        # Redraw screen at most once per second — decouple from LED cycle rate
        now = time.time()
        if now - last_draw >= 1.0:
            display.draw_party_screen(r, g, b)
            last_draw = now

        time.sleep(1.0 / speed)


def start_party_mode():
    with state.party_lock:
        state.party_active = True
        state.party_hue    = 0.0
    state.party_thread = threading.Thread(target=_party_thread_func, daemon=True)
    state.party_thread.start()


def stop_party_mode():
    """Signal thread to stop and wait for it to finish before returning."""
    with state.party_lock:
        state.party_active = False
    if state.party_thread is not None:
        state.party_thread.join(timeout=1.0)
        state.party_thread = None
    hardware.set_trackball_color(0, 0, 0)

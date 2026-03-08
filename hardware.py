import sys
import os
import subprocess
import threading
import time

import state
import logger

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

# Load persisted settings and apply them
import settings as _settings
_s = _settings.load_settings()
state.current_volume      = _s["volume"]
state.current_brightness  = _s["brightness"]
state.current_sensitivity = _s["sensitivity"]
state.SCROLL_SENSITIVITY  = 21 - state.current_sensitivity * 2
state.screen_timeout      = _s["screen_timeout"]
state.debug               = _s["debug"]
board.set_backlight(state.current_brightness)

print("Hardware initialized")


def set_trackball_color(r, g, b, w=0):
    if trackball_available:
        try:
            trackball.set_rgbw(r, g, b, w)
        except Exception:
            pass


def _make_battery_poll_fn(stop_event):
    def _run():
        while not stop_event.is_set():
            try:
                result = subprocess.run(
                    ['bash', '-c', 'echo "get battery" | nc -q 0 127.0.0.1 8423'],
                    capture_output=True, text=True, timeout=2
                )
                output = result.stdout.strip()
                if "battery:" in output:
                    val = int(float(output.split(":")[-1].strip()))
                    with state._battery_lock:
                        state._battery_level = val
                    logger.debug_log(f"Battery poll: {val}%")
            except Exception:
                pass
            stop_event.wait(30)
    return _run


_battery_stop_event = threading.Event()
_battery_thread     = threading.Thread(target=_make_battery_poll_fn(_battery_stop_event), daemon=True)
_battery_thread.start()


def stop_battery_thread():
    global _battery_thread
    _battery_stop_event.set()
    if _battery_thread and _battery_thread.is_alive():
        _battery_thread.join(timeout=3)
    _battery_thread = None


def start_battery_thread():
    global _battery_thread, _battery_stop_event
    _battery_stop_event = threading.Event()
    _battery_thread = threading.Thread(target=_make_battery_poll_fn(_battery_stop_event), daemon=True)
    _battery_thread.start()

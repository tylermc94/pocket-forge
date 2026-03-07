import sys
import os
import subprocess
import threading
import time

import state

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


def set_trackball_color(r, g, b, w=0):
    if trackball_available:
        try:
            trackball.set_rgbw(r, g, b, w)
        except Exception:
            pass


def _battery_poll_thread():
    while True:
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
        except Exception:
            pass
        time.sleep(30)


_battery_thread = threading.Thread(target=_battery_poll_thread, daemon=True)
_battery_thread.start()

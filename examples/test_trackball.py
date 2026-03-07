#!/usr/bin/env python3
import time
from trackball import TrackBall

trackball = TrackBall(interrupt_pin=None)

print("Move the trackball and click it!")
print("Ctrl+C to exit")

try:
    while True:
        up, down, left, right, switch, state = trackball.read()
        
        if left or right or up or down:
            print(f"Movement - Left: {left}, Right: {right}, Up: {up}, Down: {down}")
        
        if switch:
            print("CLICK!")
            # Flash the LED
            trackball.set_rgbw(255, 0, 0, 0)  # Red
            time.sleep(0.1)
            trackball.set_rgbw(0, 0, 0, 0)  # Off
        
        time.sleep(0.01)
        
except KeyboardInterrupt:
    print("\nExiting...")
    trackball.set_rgbw(0, 0, 0, 0)
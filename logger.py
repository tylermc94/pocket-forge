import time


def debug_log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

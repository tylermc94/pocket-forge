import state


def debug_log(message):
    if state.debug:
        print(f"[DEBUG] {message}")

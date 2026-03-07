import json
import os

SETTINGS_PATH = "/home/admin/pocket-forge/settings.json"

DEFAULTS = {
    "volume":         50,
    "brightness":    100,
    "sensitivity":     5,
    "screen_timeout": 60,
}


def load_settings():
    try:
        with open(SETTINGS_PATH, 'r') as f:
            data = json.load(f)
        # Merge: only accept known keys, fall back to defaults for missing/invalid ones
        result = dict(DEFAULTS)
        for k in DEFAULTS:
            if k in data and isinstance(data[k], (int, float)):
                result[k] = int(data[k])
        return result
    except Exception:
        return dict(DEFAULTS)


def save_settings():
    import state
    data = {
        "volume":         state.current_volume,
        "brightness":     state.current_brightness,
        "sensitivity":    state.current_sensitivity,
        "screen_timeout": state.screen_timeout,
    }
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

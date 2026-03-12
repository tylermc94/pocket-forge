import json
import os

SETTINGS_PATH = "/home/admin/pocket-forge/settings.json"

DEFAULTS = {
    "volume":         50,
    "brightness":    100,
    "sensitivity":     5,
    "screen_timeout": 60,
    "debug":         False,
    "forge_api_url": "http://labpi.local:8080/query",
    "forge_api_key": "forge_api_key_2026_secure_workshop_assistant",
}


def load_settings():
    try:
        with open(SETTINGS_PATH, 'r') as f:
            data = json.load(f)
        # Merge: only accept known keys, fall back to defaults for missing/invalid ones
        result = dict(DEFAULTS)
        for k in DEFAULTS:
            if k not in data:
                continue
            if k == "debug":
                result[k] = bool(data[k])
            elif k in ("forge_api_url", "forge_api_key"):
                if isinstance(data[k], str):
                    result[k] = data[k]
            elif isinstance(data[k], (int, float)):
                result[k] = int(data[k])
        return result
    except Exception:
        return dict(DEFAULTS)


def save_settings():
    import state
    # Start from current file to preserve forge_api_url, forge_api_key, and any
    # other fields not managed through the UI.
    existing = {}
    try:
        with open(SETTINGS_PATH, 'r') as f:
            existing = json.load(f)
    except Exception:
        pass

    existing.update({
        "volume":         state.current_volume,
        "brightness":     state.current_brightness,
        "sensitivity":    state.current_sensitivity,
        "screen_timeout": state.screen_timeout,
        "debug":          state.debug,
    })
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(existing, f)
    except Exception:
        pass

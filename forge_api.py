import io
import json
import time
import wave

import logger

SETTINGS_PATH = "/home/admin/pocket-forge/settings.json"


def _load_forge_settings():
    """Read forge_api_url and forge_api_key from settings.json each call so
    changes take effect without restarting."""
    try:
        with open(SETTINGS_PATH, 'r') as f:
            data = json.load(f)
        url = data.get("forge_api_url", "http://labpi.local:8080/query")
        key = data.get("forge_api_key", "")
        return url, key
    except Exception:
        return "http://labpi.local:8080/query", ""


def query_forge(audio_bytes):
    """POST audio_bytes (16kHz mono WAV) to the Forge API.

    Returns the parsed JSON dict on success (keys: transcript, response, audio),
    or None on any failure (timeout, connection error, bad status, missing key).
    """
    try:
        import requests
    except ImportError:
        logger.debug_log("forge_api: requests library not installed")
        return None

    url, api_key = _load_forge_settings()

    if not api_key:
        logger.debug_log("forge_api: forge_api_key not set in settings.json")
        return None

    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"audio": ("recording.wav", io.BytesIO(audio_bytes), "audio/wav")}

    t_start = time.time()
    try:
        response = requests.post(url, headers=headers, files=files, timeout=15)
        t_elapsed = time.time() - t_start

        if response.status_code != 200:
            logger.debug_log(
                f"forge_api: HTTP {response.status_code} after {t_elapsed:.1f}s"
            )
            return None

        data = response.json()
        data["_response_time"] = round(t_elapsed, 2)
        logger.debug_log(
            f"forge_api: {t_elapsed:.1f}s | transcript={data.get('transcript', '')!r}"
        )
        return data

    except requests.exceptions.Timeout:
        logger.debug_log("forge_api: request timed out after 15s")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.debug_log(f"forge_api: connection error — {e}")
        return None
    except Exception as e:
        logger.debug_log(f"forge_api: unexpected error — {e}")
        return None

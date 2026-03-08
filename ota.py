import subprocess

import state
import display
from logger import debug_log

REPO_DIR = '/home/admin/pocket-forge'


def check_for_update():
    """Returns True if update available, False if up to date, None on error."""
    try:
        debug_log("OTA: starting git fetch")
        fetch_result = subprocess.run(
            ['git', 'fetch'],
            cwd=REPO_DIR,
            capture_output=True, text=True, timeout=15
        )
        debug_log(f"OTA: git fetch returncode={fetch_result.returncode}, stderr={fetch_result.stderr.strip()}")

        local_result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=REPO_DIR,
            capture_output=True, text=True
        )
        local = local_result.stdout.strip()
        debug_log(f"OTA: local HEAD={local}")

        remote_result = subprocess.run(
            ['git', 'rev-parse', 'origin/main'],
            cwd=REPO_DIR,
            capture_output=True, text=True
        )
        remote = remote_result.stdout.strip()
        debug_log(f"OTA: origin/main={remote}")

        if local == remote:
            debug_log("OTA: up to date")
            return False
        else:
            debug_log(f"OTA: update available (local != remote)")
            return True
    except Exception as e:
        debug_log(f"OTA check error: {e}")
        return None


def apply_update():
    """Runs git pull then restarts service. Returns (success, message)."""
    try:
        result = subprocess.run(
            ['git', 'pull'],
            cwd=REPO_DIR,
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return False, f"Pull failed: {result.stderr.strip()}"
        subprocess.Popen(['sudo', 'systemctl', 'restart', 'pocket-forge'])
        return True, "Restarting..."
    except Exception as e:
        return False, f"Error: {str(e)}"


def handle_ota():
    """Called from Settings > Software Update (legacy entry point)."""
    display.draw_ota_result("Checking for updates...", color=(200, 200, 200))
    has_update = check_for_update()

    if has_update is None:
        state.current_state = state.AppState.OTA_RESULT
        display.draw_ota_result("Could not reach server. Check WiFi.", color=(255, 100, 100), pause=2)
    elif not has_update:
        state.current_state = state.AppState.OTA_RESULT
        display.draw_ota_result("Already up to date!", color=(0, 255, 0), pause=2)
    else:
        state.current_state = state.AppState.OTA_CONFIRM
        state.menu_index    = 0
        display.draw_ota_confirm()


def handle_about():
    """Entry point for About screen — checks for update and draws About screen."""
    display.draw_about_checking()
    has_update = check_for_update()
    state.current_state   = state.AppState.ABOUT
    state.about_has_update = has_update
    display.draw_about_screen(has_update)

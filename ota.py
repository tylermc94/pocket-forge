import subprocess

import state
import display


def check_for_update():
    """Returns True if update available, False if up to date, None on error."""
    try:
        subprocess.run(
            ['git', 'fetch'],
            cwd='/home/admin/pocket-forge',
            capture_output=True, timeout=15
        )
        local = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd='/home/admin/pocket-forge',
            capture_output=True, text=True
        ).stdout.strip()
        remote = subprocess.run(
            ['git', 'rev-parse', 'origin/main'],
            cwd='/home/admin/pocket-forge',
            capture_output=True, text=True
        ).stdout.strip()
        return local != remote
    except Exception as e:
        print(f"OTA check error: {e}")
        return None


def apply_update():
    """Runs git pull then restarts service. Returns (success, message)."""
    try:
        result = subprocess.run(
            ['git', 'pull'],
            cwd='/home/admin/pocket-forge',
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return False, f"Pull failed: {result.stderr.strip()}"
        subprocess.Popen(['sudo', 'systemctl', 'restart', 'pocket-forge'])
        return True, "Restarting..."
    except Exception as e:
        return False, f"Error: {str(e)}"


def handle_ota():
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

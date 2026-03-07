import subprocess
import threading

import state

REPO_PATH = '/home/admin/pocket-forge'


def fetch_update_status():
    """Start a background thread that runs git fetch and compares HEAD to
    origin/main.  Sets state.ota_status and state.ota_status_changed when done."""
    def _worker():
        try:
            subprocess.run(
                ['git', 'fetch'],
                cwd=REPO_PATH,
                capture_output=True, timeout=15
            )
            local = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=REPO_PATH,
                capture_output=True, text=True
            ).stdout.strip()
            remote = subprocess.run(
                ['git', 'rev-parse', 'origin/main'],
                cwd=REPO_PATH,
                capture_output=True, text=True
            ).stdout.strip()
            state.ota_status = "update_available" if local != remote else "up_to_date"
        except Exception as e:
            print(f"OTA fetch error: {e}")
            state.ota_status = "up_to_date"
        state.ota_status_changed = True

    threading.Thread(target=_worker, daemon=True).start()


def apply_update():
    """Runs git pull then restarts the service. Returns (success, message)."""
    try:
        result = subprocess.run(
            ['git', 'pull'],
            cwd=REPO_PATH,
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return False, f"Pull failed: {result.stderr.strip()}"
        subprocess.Popen(['sudo', 'systemctl', 'restart', 'pocket-forge'])
        return True, "Restarting..."
    except Exception as e:
        return False, f"Error: {str(e)}"

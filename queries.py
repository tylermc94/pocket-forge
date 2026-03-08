import json
import os

QUERY_LOG_PATH = "/home/admin/pocket-forge/query_log.json"
MAX_ENTRIES = 50


def log_query(entry):
    """Append an entry to the rolling query log (max 50 entries)."""
    entries = []
    if os.path.exists(QUERY_LOG_PATH):
        try:
            with open(QUERY_LOG_PATH, 'r') as f:
                entries = json.load(f)
        except (json.JSONDecodeError, IOError):
            entries = []

    entries.append(entry)
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]

    try:
        with open(QUERY_LOG_PATH, 'w') as f:
            json.dump(entries, f, indent=2)
    except IOError as e:
        print(f"Failed to write query log: {e}")

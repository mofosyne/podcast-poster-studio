"""Your poster data, kept beside config.json rather than inside it.

config.json holds settings. What you build up while using the studio lives in
its own files in the same folder:

  draft.json          the poster being made (its slots)
  shortlist.json      items kept for a later poster
  channel-notes.json  your notes and default tags for each followed feed

load() returns settings and data together, so code can keep reading
config["slots"] and friends; save() splits them back out. Configs from before
this split kept the data inside config.json: those keys are read from there
and moved to their own files on the next save.
"""

import json
import uuid
from pathlib import Path

STATE_FILES = {
    "slots": "draft.json",
    "shortlist": "shortlist.json",
    "subscription_metadata": "channel-notes.json",
}
DEFAULTS = {"slots": list, "shortlist": list, "subscription_metadata": dict}


def state_path(config_path, key):
    return Path(config_path).parent / STATE_FILES[key]


def to_text(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def load(config_path):
    """Settings from config.json plus the draft, shortlist, and channel notes."""
    config_path = Path(config_path)
    with config_path.open(encoding="utf-8") as config_file:
        config = json.load(config_file)
    for key in STATE_FILES:
        if key in config:
            continue  # Not yet moved out of an older config.json.
        path = state_path(config_path, key)
        if path.is_file():
            config[key] = json.loads(path.read_text(encoding="utf-8"))
        else:
            config[key] = DEFAULTS[key]()
    return config


def save(config_path, config):
    """Write settings to config.json and each kind of data to its own file."""
    config_path = Path(config_path)
    for key in STATE_FILES:
        if key not in config:
            continue
        path = state_path(config_path, key)
        text = to_text(config[key])
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            write_text(path, text)
    write_text(config_path, to_text({key: value for key, value in config.items() if key not in STATE_FILES}))


def migrate(config_path):
    """Move data still inside an older config.json out to its own files."""
    config_path = Path(config_path)
    with config_path.open(encoding="utf-8") as config_file:
        raw = json.load(config_file)
    if any(key in raw for key in STATE_FILES):
        save(config_path, load(config_path))
        return True
    return False

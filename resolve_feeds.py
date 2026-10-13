"""
Step 1: Resolve show names in user-data/config.json against the OPML subscription list.
Prints feed URLs to fetch, and writes a lookup file for the next step.

Usage: python3 resolve_feeds.py
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "user-data" / "config.json"

if not CONFIG_PATH.is_file():
    raise SystemExit("User config not found; run `just setup` to create user-data/config.json.")
with CONFIG_PATH.open(encoding="utf-8") as f:
    config = json.load(f)

opml_path = Path(config["opml_path"])
if not opml_path.is_absolute():
    opml_path = BASE_DIR / opml_path
if not opml_path.is_file():
    raise SystemExit(
        f"OPML file not found: {opml_path}\n"
        "Place your AntennaPod OPML export there or update opml_path in user-data/config.json."
    )

tree = ET.parse(opml_path)
root = tree.getroot()
outlines = root.findall(".//outline")

all_feeds = {}
for o in outlines:
    text = o.attrib.get("text")
    url = o.attrib.get("xmlUrl")
    if text and url:
        all_feeds[text.strip()] = url

resolved = {}
missing = []
shows = list(dict.fromkeys(slot["show"] for slot in config.get("slots", []) if slot.get("show")))
for show in shows:
    if show in all_feeds:
        resolved[show] = all_feeds[show]
    else:
        # fuzzy: case-insensitive substring match
        matches = [name for name in all_feeds if show.lower() in name.lower()]
        if len(matches) == 1:
            resolved[show] = all_feeds[matches[0]]
        elif len(matches) > 1:
            missing.append((show, f"ambiguous, matches: {matches}"))
        else:
            missing.append((show, "no match found in OPML"))

output_path = BASE_DIR / "user-data" / "resolved_feeds.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", encoding="utf-8") as f:
    json.dump(resolved, f, indent=2)

print("Resolved:")
for show, url in resolved.items():
    print(f"  {show} -> {url}")

if missing:
    print("\nNOT FOUND (check spelling against your OPML show names):")
    for show, reason in missing:
        print(f"  {show}: {reason}")

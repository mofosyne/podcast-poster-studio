"""Items added by hand, kept as one RSS feed per media type.

A single video, episode, or article you paste in is not a subscription, so it
does not belong in the OPML. Instead each media type has its own feed file under
user-data/feeds/ (added-podcasts.xml, added-videos.xml, added-articles.xml). They
are ordinary RSS 2.0 using the iTunes and Media RSS namespaces, so any feed
reader can follow them; only the studio's own bookkeeping (when an item was
added, whether its details have been fetched, its cached artwork) uses the
small pps: namespace, which other readers ignore.

Callers hold a lock around read-modify-write sequences; this module does no locking.
"""

import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path

from fetch_episodes import MEDIA_TYPES, format_duration
from link_preview import bare_link, clean_text, display_date, site_root

ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
MEDIA = "http://search.yahoo.com/mrss/"
PPS = "https://github.com/mofosyne/podcast-poster-studio/ns/1"
for prefix, uri in (("itunes", ITUNES), ("media", MEDIA), ("pps", PPS)):
    ET.register_namespace(prefix, uri)

FEED_FILES = {"podcast": "added-podcasts.xml", "video": "added-videos.xml", "article": "added-articles.xml"}
FEED_TITLES = {"podcast": "Added episodes", "video": "Added videos", "article": "Added articles"}
MAX_ITEMS_PER_FEED = 500
MAX_SUMMARY_CHARS = 400
STATUSES = ("pending", "ready", "failed")
# Fields you can write yourself when adding an item. A fetch never replaces them.
CUSTOM_FIELDS = ("episode", "summary", "tags")


def feed_path(directory, media):
    return Path(directory) / FEED_FILES[media]


def parse_time(value):
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            moment = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def complete(entry):
    """Fill in the display fields derived from what is stored."""
    published = parse_time(entry.get("published_at"))
    added = parse_time(entry.get("added_at")) or datetime.now(timezone.utc)
    entry["date"] = display_date(published) if published else f"Added {display_date(added)}"
    entry["custom"] = [field for field in CUSTOM_FIELDS if field in (entry.get("custom") or [])]
    if entry.get("description") and "summary" not in entry["custom"]:
        entry["summary"] = clean_text(entry["description"], MAX_SUMMARY_CHARS)
    if entry.get("duration_seconds"):
        entry["duration"] = format_duration(str(entry["duration_seconds"]))
    entry.setdefault("feed_url", site_root(entry["url"]))
    entry.setdefault("show", entry["url"])
    entry.setdefault("episode", entry["url"])
    entry.setdefault("tags", [])
    entry.setdefault("status", "pending")
    return entry


def read_items(directory, media):
    path = feed_path(directory, media)
    if not path.is_file():
        return []
    root = ET.parse(path).getroot()
    items = []
    for node in root.iter("item"):
        def text(tag):
            child = node.find(tag)
            return (child.text or "").strip() if child is not None and child.text else ""

        url = text("link") or text("guid")
        if not url:
            continue
        entry = {"url": url, "media": media}
        for key, tag in (
            ("episode", "title"),
            ("show", f"{{{ITUNES}}}author"),
            ("feed_url", f"{{{PPS}}}channel"),
            ("description", "description"),
            ("added_at", f"{{{PPS}}}addedAt"),
            ("status", f"{{{PPS}}}status"),
            ("error", f"{{{PPS}}}error"),
            ("artwork_path", f"{{{PPS}}}artwork"),
            ("summary", f"{{{PPS}}}summary"),
        ):
            if text(tag):
                entry[key] = text(tag)
        published = parse_time(text("pubDate"))
        date_known = node.find(f"{{{PPS}}}dateKnown")
        if published and (date_known is None or (date_known.text or "").strip() != "false"):
            entry["published_at"] = published.isoformat()
        duration = text(f"{{{ITUNES}}}duration")
        if duration.isdecimal() and int(duration) > 0:
            entry["duration_seconds"] = int(duration)
        thumbnail = node.find(f"{{{MEDIA}}}thumbnail")
        if thumbnail is not None and thumbnail.get("url"):
            entry["image_url"] = thumbnail.get("url")
        entry["tags"] = [category.text.strip() for category in node.findall("category") if category.text and category.text.strip()]
        entry["custom"] = text(f"{{{PPS}}}custom").split()
        if entry.get("status") not in STATUSES:
            entry["status"] = "pending"
        items.append(complete(entry))
    return items


def read_all(directory):
    return [item for media in MEDIA_TYPES for item in read_items(directory, media)]


def write_items(directory, media, items):
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = FEED_TITLES[media]
    ET.SubElement(channel, "link").text = "https://github.com/mofosyne/podcast-poster-studio"
    ET.SubElement(channel, "description").text = f"{FEED_TITLES[media]} by hand in Poster Studio."
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(datetime.now(timezone.utc), usegmt=True)
    ET.SubElement(channel, f"{{{PPS}}}media").text = media
    for entry in items:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = entry.get("episode") or entry["url"]
        ET.SubElement(item, "link").text = entry["url"]
        ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = entry["url"]
        published = parse_time(entry.get("published_at"))
        dated = published or parse_time(entry.get("added_at")) or datetime.now(timezone.utc)
        # Feeds need a date; an undated item uses the day it was added and says so.
        ET.SubElement(item, "pubDate").text = format_datetime(dated.astimezone(timezone.utc), usegmt=True)
        if not published:
            ET.SubElement(item, f"{{{PPS}}}dateKnown").text = "false"
        if entry.get("show"):
            ET.SubElement(item, f"{{{ITUNES}}}author").text = entry["show"]
        if entry.get("feed_url"):
            ET.SubElement(item, f"{{{PPS}}}channel").text = entry["feed_url"]
        if entry.get("description"):
            ET.SubElement(item, "description").text = entry["description"]
        if entry.get("duration_seconds"):
            ET.SubElement(item, f"{{{ITUNES}}}duration").text = str(int(entry["duration_seconds"]))
        if entry.get("image_url"):
            ET.SubElement(item, f"{{{MEDIA}}}thumbnail", {"url": entry["image_url"]})
        for tag in entry.get("tags") or []:
            ET.SubElement(item, "category").text = tag
        ET.SubElement(item, f"{{{PPS}}}addedAt").text = entry.get("added_at") or datetime.now(timezone.utc).isoformat()
        ET.SubElement(item, f"{{{PPS}}}status").text = entry.get("status", "pending")
        if entry.get("error"):
            ET.SubElement(item, f"{{{PPS}}}error").text = entry["error"][:300]
        if entry.get("artwork_path"):
            ET.SubElement(item, f"{{{PPS}}}artwork").text = str(entry["artwork_path"])
        custom = [field for field in CUSTOM_FIELDS if field in (entry.get("custom") or [])]
        if custom:
            ET.SubElement(item, f"{{{PPS}}}custom").text = " ".join(custom)
        if "summary" in custom and entry.get("summary"):
            ET.SubElement(item, f"{{{PPS}}}summary").text = entry["summary"]
    ET.indent(rss)
    path = feed_path(directory, media)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_bytes(ET.tostring(rss, encoding="utf-8", xml_declaration=True) + b"\n")
    temporary.replace(path)


def find(directory, url):
    return next((item for item in read_all(directory) if item["url"] == url), None)


def add(directory, urls, media, now=None, details=None):
    """Save bare items for new URLs; returns the URLs actually added (known ones are skipped).

    details maps a URL to fields you wrote yourself (title as "episode", summary,
    tags); they are kept when the item's details are fetched later.
    """
    if media not in MEDIA_TYPES:
        raise ValueError('Media type must be "podcast", "video", or "article".')
    known = {item["url"] for item in read_all(directory)}
    new = [url for url in dict.fromkeys(urls) if url not in known]
    if not new:
        return []
    items = read_items(directory, media)
    if len(items) + len(new) > MAX_ITEMS_PER_FEED:
        raise ValueError(f"{FEED_TITLES[media]} holds at most {MAX_ITEMS_PER_FEED} items. Remove some before adding more.")
    entries = []
    for url in new:
        entry = bare_link(url, now)
        custom = {key: value for key, value in ((details or {}).get(url) or {}).items() if key in CUSTOM_FIELDS and value}
        entry.update(custom)
        entry["custom"] = list(custom)
        entries.append(entry)
    write_items(directory, media, items + entries)
    return new


def remove(directory, url):
    for media in MEDIA_TYPES:
        items = read_items(directory, media)
        remaining = [item for item in items if item["url"] != url]
        if len(remaining) != len(items):
            write_items(directory, media, remaining)
            return
    raise ValueError("That item is not in your added items.")


def move(directory, url, media):
    """Change an item's media type by moving it to that type's feed."""
    if media not in MEDIA_TYPES:
        raise ValueError('Media type must be "podcast", "video", or "article".')
    item = find(directory, url)
    if item is None:
        raise ValueError("That item is not in your added items.")
    if item["media"] == media:
        return item
    remove(directory, url)
    write_items(directory, media, read_items(directory, media) + [item])
    item["media"] = media
    return item


def update(directory, url, details):
    """Replace an item's fetched details, keeping when and where it was added."""
    for media in MEDIA_TYPES:
        items = read_items(directory, media)
        for index, item in enumerate(items):
            if item["url"] != url:
                continue
            updated = {**details, "url": url, "media": media, "added_at": item.get("added_at")}
            # What you wrote yourself wins over fetched details.
            for field in item.get("custom") or []:
                if field in item:
                    updated[field] = item[field]
            updated["custom"] = item.get("custom") or []
            items[index] = complete(updated)
            write_items(directory, media, items)
            return items[index]
    raise ValueError("That item was removed while its details were being fetched.")

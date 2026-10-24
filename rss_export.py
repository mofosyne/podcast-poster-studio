"""Your shortlist and poster archive as RSS feeds.

Served at /feeds/shortlist.xml and /feeds/posters.xml so a feed reader (or another
app on this computer) can follow what you have shortlisted and what you have
printed. Built on demand from the saved shortlist and the poster history.
"""

import html
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import quote

from added_feeds import ITUNES, PPS
from fetch_episodes import media_type_for


def rss_channel(title, description, link):
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "link").text = link
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(datetime.now(timezone.utc), usegmt=True)
    return rss, channel


def to_bytes(rss):
    ET.indent(rss)
    return ET.tostring(rss, encoding="utf-8", xml_declaration=True) + b"\n"


def display_date_to_rss(text):
    """'October 12, 2026' (or 'Added October 12, 2026') as an RSS date, else None."""
    text = str(text or "").removeprefix("Added ").strip()
    try:
        moment = datetime.strptime(text, "%B %d, %Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return format_datetime(moment, usegmt=True)


def shortlist_rss(entries, base_url):
    rss, channel = rss_channel("Shortlist", "Episodes, videos, and articles shortlisted in Poster Studio for a later poster.", f"{base_url}/#pick")
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("url"):
            continue
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = entry.get("episode") or entry["url"]
        ET.SubElement(item, "link").text = entry["url"]
        ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = entry["url"]
        published = display_date_to_rss(entry.get("date"))
        if published:
            ET.SubElement(item, "pubDate").text = published
        if entry.get("show"):
            ET.SubElement(item, f"{{{ITUNES}}}author").text = entry["show"]
        if entry.get("summary"):
            ET.SubElement(item, "description").text = entry["summary"]
        for tag in entry.get("tags") or []:
            ET.SubElement(item, "category").text = tag
        ET.SubElement(item, f"{{{PPS}}}media").text = media_type_for(entry)
    return to_bytes(rss)


def posters_rss(records, base_url, pdf_size=None):
    """One item per archived poster, with its PDF as an enclosure."""
    rss, channel = rss_channel("Posters", "Posters made in Poster Studio, newest first.", f"{base_url}/#history")
    for record in records:
        manifest = record.get("manifest")
        if not manifest:
            continue
        name = quote(manifest)
        item = ET.SubElement(channel, "item")
        edition = record.get("edition") or ""
        ET.SubElement(item, "title").text = " · ".join(part for part in (record.get("title") or "Poster", edition) if part)
        ET.SubElement(item, "link").text = f"{base_url}/api/history/{name}/pdf"
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = manifest
        try:
            generated = datetime.fromisoformat(record.get("generated_at", ""))
            ET.SubElement(item, "pubDate").text = format_datetime(generated.astimezone(timezone.utc), usegmt=True)
        except ValueError:
            pass
        slots = [slot for slot in record.get("slots") or [] if isinstance(slot, dict)]
        listing = "".join(
            f'<li><a href="{html.escape(slot.get("url") or "", quote=True)}">{html.escape(slot.get("episode") or slot.get("url") or "")}</a>'
            f' — {html.escape(slot.get("show") or "")}</li>'
            for slot in slots
        )
        ET.SubElement(item, "description").text = f"<ol>{listing}</ol>"
        size = pdf_size(record) if pdf_size else None
        if size:
            ET.SubElement(item, "enclosure", {"url": f"{base_url}/api/history/{name}/download", "type": "application/pdf", "length": str(size)})
        if record.get("printed_at"):
            ET.SubElement(item, f"{{{PPS}}}printedAt").text = record["printed_at"]
    return to_bytes(rss)

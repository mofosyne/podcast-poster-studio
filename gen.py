import colorsys
import datetime
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import qrcode
from PIL import Image, ImageOps, UnidentifiedImageError
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from fetch_episodes import scan_feed

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "user-data" / "config.json"
MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024
USER_AGENT = "PodcastPoster/1.0 (local poster generator)"

if not CONFIG_PATH.is_file():
    raise SystemExit("User config not found; run `just setup` to create user-data/config.json.")
with CONFIG_PATH.open(encoding="utf-8") as f:
    config = json.load(f)

slots = config.get("slots", [])
if not slots:
    raise SystemExit("user-data/config.json must define at least one poster slot")
if len(slots) > 8:
    raise SystemExit("user-data/config.json supports at most eight poster slots")

poster_period = config.get("poster_period", "month").lower()
if poster_period not in {"month", "week"}:
    raise SystemExit('user-data/config.json "poster_period" must be "month" or "week"')

now = datetime.date.today()
if poster_period == "month":
    edition_label = now.strftime("%B %Y").upper()
else:
    week_start = now - datetime.timedelta(days=now.weekday())
    edition_label = f"WEEK OF {week_start.strftime('%B')} {week_start.day}, {week_start.year}".upper()

poster_title = config["poster_title"].format(period=poster_period.upper())


def project_path(config_key):
    path = Path(config[config_key])
    return path if path.is_absolute() else BASE_DIR / path


def resolve_slots():
    feed_cache_dir = project_path("feed_cache_dir") / "feeds"
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    resolved = []

    for slot in slots:
        slot_type = slot.get("type")
        show = slot.get("show")
        if not show:
            raise ValueError(f"Poster slot has no show name: {slot}")

        if slot_type == "fixed":
            missing = [key for key in ("episode", "date", "url") if not slot.get(key)]
            if missing:
                raise ValueError(f"Fixed slot for {show} is missing: {', '.join(missing)}")
            resolved.append({**slot, "slot_type": slot_type})
        elif slot_type == "latest":
            feed_url = slot.get("feed_url")
            if not feed_url:
                raise ValueError(f"Latest slot for {show} needs a feed_url")
            episodes, status, error = scan_feed(show, feed_url, feed_cache_dir, now_utc)
            if error:
                print(f"Feed note for {show}: {error}", file=sys.stderr)
            if not episodes:
                raise RuntimeError(f"Could not resolve latest episode for {show} ({status})")
            latest = max(episodes, key=lambda episode: episode["published_at"])
            resolved.append({**latest, "slot_type": slot_type})
        else:
            raise ValueError(f"Unknown slot type for {show}: {slot_type!r}")

    return resolved


def archive_generation(pdf_path, items):
    history_dir = project_path("poster_history_dir")
    history_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.datetime.now().astimezone()
    base_name = f"poster-{generated_at.strftime('%Y%m%d-%H%M%S')}"
    archive_pdf = history_dir / f"{base_name}.pdf"
    archive_json = history_dir / f"{base_name}.json"
    suffix = 2
    while archive_pdf.exists() or archive_json.exists():
        archive_pdf = history_dir / f"{base_name}-{suffix}.pdf"
        archive_json = history_dir / f"{base_name}-{suffix}.json"
        suffix += 1

    shutil.copy2(pdf_path, archive_pdf)
    snapshot = {
        "generated_at": generated_at.isoformat(),
        "title": poster_title,
        "period": poster_period,
        "edition": edition_label,
        "pdf": archive_pdf.name,
        "slots": items,
    }
    archive_json.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return archive_pdf, archive_json


def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


def artwork_url_from_feed(feed_url):
    request = Request(feed_url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=15) as response:
        feed_data = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(feed_data) > MAX_DOWNLOAD_BYTES:
        raise ValueError("feed is larger than 15 MB")

    root = ET.fromstring(feed_data)
    channel = next((node for node in root.iter() if local_name(node.tag) == "channel"), root)

    for node in channel:
        name = local_name(node.tag)
        if name == "image":
            if node.get("href"):
                return urljoin(feed_url, node.get("href"))
            for child in node:
                if local_name(child.tag) == "url" and child.text:
                    return urljoin(feed_url, child.text.strip())
        elif name in {"logo", "icon"} and node.text:
            return urljoin(feed_url, node.text.strip())

    latest_item = next((node for node in channel if local_name(node.tag) in {"item", "entry"}), None)
    if latest_item is not None:
        for node in latest_item.iter():
            if local_name(node.tag) in {"image", "thumbnail"}:
                image_url = node.get("href") or node.get("url")
                if image_url:
                    return urljoin(feed_url, image_url)

    return None


class SocialImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image_url = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        values = dict(attrs)
        key = (values.get("property") or values.get("name") or "").lower()
        if key in {"og:image", "twitter:image"} and values.get("content"):
            self.image_url = values["content"]


def artwork_url_from_page(page_url):
    request = Request(page_url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=15) as response:
        page_data = response.read(2 * 1024 * 1024)
        encoding = response.headers.get_content_charset() or "utf-8"
    parser = SocialImageParser()
    parser.feed(page_data.decode(encoding, errors="replace"))
    return urljoin(page_url, parser.image_url) if parser.image_url else None


def artwork_for(item):
    feed_url = item.get("feed_url")
    page_url = item.get("url")
    if not feed_url and not page_url:
        return None

    cache_key = feed_url or page_url
    cache_dir = project_path("feed_cache_dir") / "artwork"
    cache_path = cache_dir / f"{hashlib.sha256(cache_key.encode()).hexdigest()}.png"
    if cache_path.is_file():
        return cache_path

    try:
        image_url = None
        if feed_url:
            try:
                image_url = artwork_url_from_feed(feed_url)
            except (OSError, URLError, ET.ParseError, ValueError):
                pass
        if not image_url and page_url:
            image_url = artwork_url_from_page(page_url)
        if not image_url:
            raise ValueError("no channel artwork or episode-page preview image found")

        request = Request(image_url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=20) as response:
            image_data = response.read(MAX_DOWNLOAD_BYTES + 1)
        if len(image_data) > MAX_DOWNLOAD_BYTES:
            raise ValueError("artwork image is larger than 15 MB")

        with Image.open(BytesIO(image_data)) as source:
            artwork = ImageOps.fit(source.convert("RGB"), (512, 512))
        cache_dir.mkdir(parents=True, exist_ok=True)
        artwork.save(cache_path, format="PNG", optimize=True)
        print(f"Artwork cached for {item['show']}")
        return cache_path
    except (OSError, URLError, ET.ParseError, ValueError, UnidentifiedImageError) as error:
        print(f"Artwork unavailable for {item['show']}: {error}", file=sys.stderr)
        return None


def draw_placeholder_artwork(pdf, x, y, size, show):
    pdf.saveState()
    pdf.setFillColor(colors.HexColor("#172b2a"))
    pdf.roundRect(x, y, size, size, 2 * mm, fill=1, stroke=0)

    digest = hashlib.sha256(show.casefold().encode("utf-8")).digest()
    hue = int.from_bytes(digest[:2], "big") / 65535
    accent = colors.Color(*colorsys.hsv_to_rgb(hue, 0.58, 0.92))

    center_x = x + size / 2
    center_y = y + size * 0.70
    pdf.setStrokeColor(colors.HexColor("#28514d"))
    pdf.setLineWidth(0.7)
    for radius in (size * 0.18, size * 0.29):
        pdf.circle(center_x, center_y, radius, stroke=1, fill=0)

    pdf.setStrokeColor(accent)
    pdf.setLineWidth(1.2)
    pdf.roundRect(
        center_x - size * 0.07,
        center_y - size * 0.04,
        size * 0.14,
        size * 0.25,
        size * 0.07,
        stroke=1,
        fill=0,
    )
    pdf.arc(
        center_x - size * 0.15,
        center_y - size * 0.14,
        center_x + size * 0.15,
        center_y + size * 0.15,
        startAng=200,
        extent=140,
    )
    pdf.line(center_x, center_y - size * 0.14, center_x, center_y - size * 0.23)
    pdf.line(center_x - size * 0.10, center_y - size * 0.23, center_x + size * 0.10, center_y - size * 0.23)

    max_width = size * 0.88
    title_lines = []
    font_size = 8
    for font_size in (8, 7.5, 7, 6.5, 6, 5.5):
        title_lines = []
        line = ""
        for word in show.split():
            candidate = (line + " " + word).strip()
            if pdf.stringWidth(candidate, "Helvetica-Bold", font_size) > max_width and line:
                title_lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            title_lines.append(line)
        if len(title_lines) <= 4:
            break

    leading = font_size * 1.08
    text_y = y + size * 0.055 + (len(title_lines) - 1) * leading
    pdf.setFillColor(colors.HexColor("#f0f5f4"))
    pdf.setFont("Helvetica-Bold", font_size)
    for line in title_lines:
        pdf.drawCentredString(center_x, text_y, line)
        text_y -= leading
    pdf.restoreState()


data = resolve_slots()

output_pdf = project_path("output_pdf")
output_pdf.parent.mkdir(parents=True, exist_ok=True)

W, H = A4
c = canvas.Canvas(str(output_pdf), pagesize=A4)

margin = 18 * mm
c.setFillColor(colors.HexColor("#1a1a1a"))
c.rect(0, 0, W, H, fill=1, stroke=0)

c.setFillColor(colors.white)
title_font_size = 30
while c.stringWidth(poster_title, "Helvetica-Bold", title_font_size) > W - 2 * margin:
    title_font_size -= 0.5
c.setFont("Helvetica-Bold", title_font_size)
c.drawCentredString(W / 2, H - margin - 10 * mm, poster_title)
c.setFont("Helvetica", 12)
c.setFillColor(colors.HexColor("#aaaaaa"))
c.drawCentredString(W / 2, H - margin - 18 * mm, "A curated selection of episodes - scan to listen")

row_h = (H - margin * 2 - 28 * mm) / len(data)
top = H - margin - 28 * mm

for i, item in enumerate(data):
    y_top = top - i * row_h
    y_center = y_top - row_h / 2
    artwork_path = artwork_for(item)
    artwork_size = row_h * 0.76
    artwork_x = margin
    artwork_y = y_center - artwork_size / 2

    if artwork_path:
        c.drawImage(str(artwork_path), artwork_x, artwork_y, width=artwork_size, height=artwork_size)
    else:
        draw_placeholder_artwork(c, artwork_x, artwork_y, artwork_size, item["show"])

    qr_size = row_h * 0.4
    qr_img = qrcode.make(item["url"], border=4)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, kind="PNG")
    qr_buffer.seek(0)

    qr_x = W - margin - qr_size
    qr_y = y_center - qr_size / 2
    c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size)

    text_x = artwork_x + artwork_size + 7 * mm
    text_w = qr_x - 7 * mm - text_x

    c.setFillColor(colors.HexColor("#4fd1c5"))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(text_x, y_center + 8 * mm, item["show"])

    c.setFillColor(colors.white)
    c.setFont("Helvetica", 12)
    words = item["episode"].split()
    lines = []
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        if c.stringWidth(test, "Helvetica", 12) > text_w:
            lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    line_y = y_center
    for line in lines[:2]:
        c.drawString(text_x, line_y, line)
        line_y -= 5.5 * mm

    date_y = line_y - 2 * mm
    c.setFillColor(colors.HexColor("#888888"))
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(text_x, date_y, item["date"])

    url_font_size = 8
    url_width = c.stringWidth(item["url"], "Helvetica", url_font_size)
    while url_width > text_w and url_font_size > 6.5:
        url_font_size -= 0.25
        url_width = c.stringWidth(item["url"], "Helvetica", url_font_size)
    url_y = date_y - 3.5 * mm
    c.setFillColor(colors.HexColor("#4fd1c5"))
    c.setFont("Helvetica", url_font_size)
    c.drawString(text_x, url_y, item["url"])
    c.linkURL(
        item["url"],
        (text_x, url_y - 0.6 * mm, text_x + min(url_width, text_w), url_y + 2.4 * mm),
        relative=0,
        thickness=0,
    )

    if i < len(data) - 1:
        c.setStrokeColor(colors.HexColor("#333333"))
        c.line(margin, y_top - row_h, W - margin, y_top - row_h)

c.setFillColor(colors.HexColor("#666666"))
c.setFont("Helvetica", 9)
c.drawCentredString(W / 2, margin / 2, edition_label)

c.save()
archive_pdf, archive_json = archive_generation(output_pdf, data)
print(f"Wrote {output_pdf}")
print(f"Archived {archive_pdf} and {archive_json}")

import argparse
import colorsys
import datetime
import hashlib
import json
import os
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
CONFIG_PATH = Path(os.environ.get("PODCAST_POSTER_CONFIG", BASE_DIR / "user-data" / "config.json"))
MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024
MAX_POSTER_SLOTS = 6
USER_AGENT = "PodcastPoster/1.0 (local poster generator)"

argument_parser = argparse.ArgumentParser(description="Generate a podcast poster PDF.")
argument_parser.add_argument("--preview", action="store_true", help="Write the preview PDF without archiving it.")
argument_parser.add_argument(
    "--regenerate-from",
    metavar="MANIFEST_JSON",
    help="Re-render an archived poster history JSON manifest in place, using its frozen slot data "
    "instead of the live config. Overwrites that entry's archived PDF and does not create a new "
    "history entry.",
)
arguments = argument_parser.parse_args()
preview_only = arguments.preview

if not CONFIG_PATH.is_file():
    raise SystemExit("User config not found; run `just setup` to create user-data/config.json.")
with CONFIG_PATH.open(encoding="utf-8") as f:
    config = json.load(f)

regenerate_manifest_path = Path(arguments.regenerate_from).resolve() if arguments.regenerate_from else None

if regenerate_manifest_path:
    if not regenerate_manifest_path.is_file():
        raise SystemExit(f"History manifest not found: {regenerate_manifest_path}")
    with regenerate_manifest_path.open(encoding="utf-8") as f:
        history_manifest = json.load(f)

    slots = history_manifest.get("slots", [])
    if not slots:
        raise SystemExit(f"{regenerate_manifest_path} has no archived slots to regenerate.")

    poster_layout = history_manifest.get("layout", "list")
    poster_theme = history_manifest.get("theme", "dark")
else:
    slots = config.get("slots", [])
    if not slots:
        raise SystemExit("user-data/config.json must define at least one poster slot")
    if len(slots) > MAX_POSTER_SLOTS:
        raise SystemExit(f"user-data/config.json supports at most {MAX_POSTER_SLOTS} poster slots")

    poster_layout = config.get("poster_layout", "list")
    if poster_layout not in {"list", "single"}:
        raise SystemExit('user-data/config.json "poster_layout" must be "list" or "single"')
    if poster_layout == "single" and len(slots) != 1:
        raise SystemExit('A "single" poster layout requires exactly one configured slot')

    poster_theme = config.get("poster_theme", "dark")
    if poster_theme not in {"dark", "ink-saving"}:
        raise SystemExit('user-data/config.json "poster_theme" must be "dark" or "ink-saving"')

THEME_PALETTES = {
    "dark": {
        "background": "#1a1a1a",
        "primary": "#ffffff",
        "secondary": "#aaaaaa",
        "muted": "#888888",
        "summary": "#c4ceca",
        "accent": "#4fd1c5",
        "divider": "#333333",
        "placeholder_background": "#172b2a",
        "placeholder_ring": "#28514d",
        "placeholder_text": "#f0f5f4",
        "tag_text": "#ffffff",
        "tag_fills": ("#135a70", "#58407d", "#386044", "#895124", "#7a354a", "#354d82", "#6d5b20", "#285f58"),
    },
    "ink-saving": {
        "background": "#ffffff",
        "primary": "#171a19",
        "secondary": "#444b48",
        "muted": "#5b625f",
        "summary": "#303633",
        "accent": "#00695c",
        "divider": "#d5d9d7",
        "placeholder_background": "#ffffff",
        "placeholder_ring": "#a9c3bd",
        "placeholder_text": "#28312e",
        "tag_text": "#25312d",
        "tag_fills": ("#d9ecff", "#f2ddf5", "#dcf1df", "#ffebd5", "#f8dce4", "#e0e7ff", "#f5efcf", "#d5f0eb"),
    },
}
THEME_COLORS = THEME_PALETTES.get(poster_theme, THEME_PALETTES["dark"])
TAG_BUBBLE_HEIGHT = 5 * mm
TAG_BUBBLE_LINE_STEP = 6 * mm
TAG_BUBBLE_HORIZONTAL_PADDING = 3.5

if regenerate_manifest_path:
    poster_period = history_manifest.get("period", "month")
    poster_title = history_manifest.get("title") or "Episodes worth listening to"
    edition_label = history_manifest.get("edition") or poster_period.upper()
else:
    poster_period = config.get("poster_period", "month").lower()
    if poster_period not in {"month", "week"}:
        raise SystemExit('user-data/config.json "poster_period" must be "month" or "week"')

    now = datetime.date.today()
    if poster_period == "month":
        edition_label = now.strftime("%B %Y").upper()
    else:
        week_start = now - datetime.timedelta(days=now.weekday())
        edition_label = f"WEEK OF {week_start.strftime('%B')} {week_start.day}, {week_start.year}".upper()

    poster_title = (
        config.get("single_poster_title", "ONE EPISODE WORTH YOUR TIME")
        if poster_layout == "single"
        else config["poster_title"].format(period=poster_period.upper())
    )


def project_path(config_key):
    path = Path(config[config_key])
    return path if path.is_absolute() else BASE_DIR / path


def apply_subscription_metadata(item, feed_url, slot):
    metadata = config.get("subscription_metadata", {})
    if not isinstance(metadata, dict):
        return item
    subscription = metadata.get(feed_url, {})
    if not isinstance(subscription, dict):
        return item

    result = dict(item)
    channel_description = subscription.get("channel_description")
    if "channel_description" not in slot and isinstance(channel_description, str) and channel_description.strip():
        result["channel_description"] = channel_description.strip()
    if "tags" not in slot and isinstance(subscription.get("tags"), list):
        result["tags"] = subscription["tags"]
    return result


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
            fixed = apply_subscription_metadata({**slot, "slot_type": slot_type}, slot.get("feed_url"), slot)
            resolved.append(fixed)
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
            resolved.append(apply_subscription_metadata({**latest, "slot_type": slot_type}, feed_url, slot))
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
        "printed_at": None,
        "title": poster_title,
        "layout": poster_layout,
        "theme": poster_theme,
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
    cached_artwork = item.get("artwork_path")
    if isinstance(cached_artwork, str) and cached_artwork.strip():
        candidate = Path(cached_artwork)
        if not candidate.is_absolute():
            candidate = (BASE_DIR / candidate).resolve()
        artwork_root = (project_path("feed_cache_dir") / "artwork").resolve()
        if candidate.is_relative_to(artwork_root) and candidate.is_file():
            return candidate

    feed_url = item.get("feed_url")
    page_url = item.get("url")
    if not feed_url and not page_url:
        return None

    cache_key = feed_url or page_url
    cache_dir = project_path("feed_cache_dir") / "artwork"
    cache_path = cache_dir / f"{hashlib.sha256(cache_key.encode()).hexdigest()}-v2.png"
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
            rgba = source.convert("RGBA")
            artwork = ImageOps.fit(rgba, (512, 512))
        cache_dir.mkdir(parents=True, exist_ok=True)
        artwork.save(cache_path, format="PNG", optimize=True)
        print(f"Artwork cached for {item['show']}")
        return cache_path
    except (OSError, URLError, ET.ParseError, ValueError, UnidentifiedImageError) as error:
        print(f"Artwork unavailable for {item['show']}: {error}", file=sys.stderr)
        return None


def draw_placeholder_artwork(pdf, x, y, size, show):
    pdf.saveState()
    pdf.setFillColor(colors.HexColor(THEME_COLORS["placeholder_background"]))
    pdf.roundRect(x, y, size, size, 2 * mm, fill=1, stroke=0)

    digest = hashlib.sha256(show.casefold().encode("utf-8")).digest()
    hue = int.from_bytes(digest[:2], "big") / 65535
    accent = colors.Color(*colorsys.hsv_to_rgb(hue, 0.58, 0.92))

    center_x = x + size / 2
    center_y = y + size * 0.70
    pdf.setStrokeColor(colors.HexColor(THEME_COLORS["placeholder_ring"]))
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
    pdf.setFillColor(colors.HexColor(THEME_COLORS["placeholder_text"]))
    pdf.setFont("Helvetica-Bold", font_size)
    for line in title_lines:
        pdf.drawCentredString(center_x, text_y, line)
        text_y -= leading
    pdf.restoreState()


def fit_pdf_text(pdf, text, font_name, font_size, max_width):
    text = text.strip()
    if pdf.stringWidth(text, font_name, font_size) <= max_width:
        return text
    suffix = "…"
    while text and pdf.stringWidth(text + suffix, font_name, font_size) > max_width:
        previous_word = text.rfind(" ")
        text = text[:previous_word].rstrip() if previous_word >= 0 else text[:-1]
    return text.rstrip() + suffix


def layout_tag_rows(pdf, tags, max_width, max_rows, font_size=7):
    """Split tags into rows of (label, width) bubbles that fit max_width."""
    cleaned_tags = ["#" + "_".join(str(tag).split()) for tag in tags if str(tag).strip()]
    rows = []
    if max_width <= 0 or max_rows <= 0:
        return rows
    pad_x = TAG_BUBBLE_HORIZONTAL_PADDING
    gap_x = 2 * mm
    row_width = 0
    for tag in cleaned_tags:
        tag_width = pdf.stringWidth(tag, "Helvetica-Bold", font_size) + 2 * pad_x
        if tag_width > max_width:
            tag = fit_pdf_text(pdf, tag, "Helvetica-Bold", font_size, max_width - 2 * pad_x)
            tag_width = pdf.stringWidth(tag, "Helvetica-Bold", font_size) + 2 * pad_x
        if not rows or row_width + gap_x + tag_width > max_width:
            if len(rows) >= max_rows:
                break
            rows.append([])
            row_width = -gap_x
        rows[-1].append((tag, tag_width))
        row_width += gap_x + tag_width
    return rows


def draw_tag_bubbles(pdf, tags, x, top_y, max_width, max_rows, font_size=7, align="left"):
    rows = layout_tag_rows(pdf, tags, max_width, max_rows, font_size)
    if not rows:
        return top_y, 0

    pad_x = TAG_BUBBLE_HORIZONTAL_PADDING
    bubble_h = TAG_BUBBLE_HEIGHT
    gap_x = 2 * mm
    line_step = TAG_BUBBLE_LINE_STEP
    palette = THEME_COLORS["tag_fills"]
    pdf.setFont("Helvetica-Bold", font_size)

    for row_index, row in enumerate(rows):
        row_width = sum(width for _, width in row) + gap_x * (len(row) - 1)
        cursor_x = x + (max_width - row_width) / 2 if align == "center" else x
        bubble_y = top_y - row_index * line_step - bubble_h
        for tag, tag_width in row:
            digest = hashlib.sha256(tag.casefold().encode("utf-8")).digest()
            fill = colors.HexColor(palette[int.from_bytes(digest[:2], "big") % len(palette)])
            pdf.setFillColor(fill)
            pdf.roundRect(cursor_x, bubble_y, tag_width, bubble_h, bubble_h / 2, fill=1, stroke=0)
            pdf.setFillColor(colors.HexColor(THEME_COLORS["tag_text"]))
            text_y = bubble_y + (bubble_h - font_size) / 2 + 0.5
            pdf.drawString(cursor_x + pad_x, text_y, tag)
            cursor_x += tag_width + gap_x

    return top_y - len(rows) * line_step, len(rows)


def draw_single_poster(pdf, item):
    # No poster heading: the episode itself leads. Artwork, then the episode
    # title, its date, the channel, tags and summary, with the QR code below.
    margin = 18 * mm
    content_width = W - 2 * margin

    # Footer: the QR code centred at the bottom, with a hint and the URL beneath.
    qr_size = 50 * mm
    url_y = margin + 3 * mm
    hint_y = url_y + 4.5 * mm
    qr_y = hint_y + 4.5 * mm
    footer_top = qr_y + qr_size

    # Measure the text first; the artwork then takes whatever height is left,
    # and the whole group is centred between the top margin and the QR code.
    title_lines, title_font_size = fit_title_lines(
        pdf, item["episode"], "Helvetica-Bold", 24, 15, content_width, 3
    )
    title_leading = title_font_size * 1.2
    subtitle = " · ".join(part for part in (item.get("date", ""), item.get("duration", "")) if part)
    show_font_size = 14
    while pdf.stringWidth(item["show"], "Helvetica-Bold", show_font_size) > content_width and show_font_size > 10:
        show_font_size -= 0.5
    tag_rows = layout_tag_rows(pdf, item.get("tags", []), content_width, 2, font_size=8)
    summary = str(item.get("summary") or "").strip()
    summary_font_size = 11
    summary_leading = summary_font_size * 1.35
    art_gap = 9 * mm
    available = H - margin - footer_top - 10 * mm
    min_artwork, max_artwork = 60 * mm, 135 * mm
    summary_max_lines = 10
    while True:
        summary_lines = wrap_pdf_text(
            pdf, summary, "Helvetica", summary_font_size, content_width - 16 * mm, summary_max_lines
        ) if summary else []
        text_height = (
            title_leading * len(title_lines)
            + (6 * mm if subtitle else 0)
            + 7 * mm
            + (len(tag_rows) * TAG_BUBBLE_LINE_STEP + 3 * mm if tag_rows else 0)
            + (summary_leading * len(summary_lines) + 3 * mm if summary_lines else 0)
        )
        artwork_size = min(max_artwork, available - art_gap - text_height)
        if artwork_size >= min_artwork or summary_max_lines <= 3:
            artwork_size = max(artwork_size, min_artwork)
            break
        summary_max_lines -= 1

    group_height = artwork_size + art_gap + text_height
    artwork_top = H - margin - max(0, available - group_height) / 2
    artwork_x = (W - artwork_size) / 2
    artwork_y = artwork_top - artwork_size
    artwork_path = artwork_for(item)
    if artwork_path:
        pdf.drawImage(str(artwork_path), artwork_x, artwork_y, width=artwork_size, height=artwork_size, mask="auto")
    else:
        draw_placeholder_artwork(pdf, artwork_x, artwork_y, artwork_size, item["show"])

    cursor_y = artwork_y - art_gap
    pdf.setFillColor(colors.HexColor(THEME_COLORS["primary"]))
    pdf.setFont("Helvetica-Bold", title_font_size)
    for line in title_lines:
        cursor_y -= title_font_size * 0.2
        pdf.drawCentredString(W / 2, cursor_y, line)
        cursor_y -= title_leading - title_font_size * 0.2
    if subtitle:
        cursor_y -= 1.5 * mm
        pdf.setFillColor(colors.HexColor(THEME_COLORS["muted"]))
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(W / 2, cursor_y, subtitle)
        cursor_y -= 4.5 * mm
    cursor_y -= 2.5 * mm
    pdf.setFillColor(colors.HexColor(THEME_COLORS["accent"]))
    pdf.setFont("Helvetica-Bold", show_font_size)
    pdf.drawCentredString(W / 2, cursor_y, fit_pdf_text(pdf, item["show"], "Helvetica-Bold", show_font_size, content_width))
    cursor_y -= 4.5 * mm
    if tag_rows:
        cursor_y -= 1 * mm
        cursor_y, _ = draw_tag_bubbles(
            pdf, item.get("tags", []), margin, cursor_y, content_width, max_rows=2, font_size=8, align="center"
        )
        cursor_y -= 1 * mm
    if summary_lines:
        cursor_y -= 3 * mm + summary_font_size * 0.4
        pdf.setFillColor(colors.HexColor(THEME_COLORS["summary"]))
        pdf.setFont("Helvetica", summary_font_size)
        for line in summary_lines:
            pdf.drawCentredString(W / 2, cursor_y, line)
            cursor_y -= summary_leading

    pdf.setFillColor(colors.HexColor(THEME_COLORS["secondary"]))
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(W / 2, hint_y, "Scan to listen, or search for it in your preferred podcast app")

    qr_image = qrcode.make(item["url"], border=4)
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, kind="PNG")
    qr_buffer.seek(0)
    pdf.drawImage(ImageReader(qr_buffer), (W - qr_size) / 2, qr_y, width=qr_size, height=qr_size)

    url_font_size = 8
    while pdf.stringWidth(item["url"], "Helvetica", url_font_size) > content_width and url_font_size > 6:
        url_font_size -= 0.25
    visible_url = fit_pdf_text(pdf, item["url"], "Helvetica", url_font_size, content_width)
    url_width = pdf.stringWidth(visible_url, "Helvetica", url_font_size)
    pdf.setFillColor(colors.HexColor(THEME_COLORS["accent"]))
    pdf.setFont("Helvetica", url_font_size)
    pdf.drawCentredString(W / 2, url_y, visible_url)
    pdf.linkURL(
        item["url"],
        ((W - url_width) / 2, url_y - 0.6 * mm, (W + url_width) / 2, url_y + 2.4 * mm),
        relative=0,
        thickness=0,
    )


def wrap_pdf_text(pdf, text, font_name, font_size, max_width, max_lines):
    """Wrap text into at most max_lines lines; max_width may be a function of the line index."""
    width_for = max_width if callable(max_width) else (lambda index: max_width)
    words = text.split()
    lines = []
    line = ""
    truncated = False
    for word in words:
        candidate = (line + " " + word).strip()
        if pdf.stringWidth(candidate, font_name, font_size) <= width_for(len(lines)):
            line = candidate
        elif line:
            lines.append(line)
            line = word
            if len(lines) == max_lines:
                truncated = True
                break
        else:
            lines.append(fit_pdf_text(pdf, word, font_name, font_size, width_for(len(lines))))
            if len(lines) == max_lines:
                truncated = True
                break
    if line and len(lines) < max_lines:
        lines.append(line)
    if truncated and lines:
        lines[-1] = fit_pdf_text(pdf, lines[-1] + "…", font_name, font_size, width_for(len(lines) - 1))
    return lines


def fit_title_lines(pdf, text, font_name, max_font_size, min_font_size, max_width, max_lines):
    font_size = max_font_size
    while True:
        lines = wrap_pdf_text(pdf, text, font_name, font_size, max_width, max_lines)
        fits = bool(lines) and not lines[-1].endswith("…")
        if fits or font_size <= min_font_size:
            return lines, font_size
        font_size -= 0.5


if regenerate_manifest_path:
    data = slots
    archive_pdf_name = history_manifest.get("pdf")
    if not archive_pdf_name:
        raise SystemExit(f"{regenerate_manifest_path} has no archived pdf filename to overwrite.")
    output_pdf = project_path("poster_history_dir") / archive_pdf_name
    if not output_pdf.is_file():
        raise SystemExit(f"Archived PDF not found: {output_pdf}")
else:
    data = resolve_slots()
    output_pdf = project_path("output_pdf")

output_pdf.parent.mkdir(parents=True, exist_ok=True)

W, H = A4
c = canvas.Canvas(str(output_pdf), pagesize=A4)

margin = 18 * mm
c.setFillColor(colors.HexColor(THEME_COLORS["background"]))
c.rect(0, 0, W, H, fill=1, stroke=0)

if poster_layout == "list":
    c.setFillColor(colors.HexColor(THEME_COLORS["primary"]))
    title_font_size = 30
    while c.stringWidth(poster_title, "Helvetica-Bold", title_font_size) > W - 2 * margin:
        title_font_size -= 0.5
    c.setFont("Helvetica-Bold", title_font_size)
    c.drawCentredString(W / 2, H - margin - 10 * mm, poster_title)
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.HexColor(THEME_COLORS["secondary"]))
    c.drawCentredString(
        W / 2, H - margin - 18 * mm, "Scan to listen, or search for it in your preferred podcast app"
    )

row_h = (H - margin * 2 - 28 * mm) / len(data)
top = H - margin - 28 * mm

for i, item in enumerate(data if poster_layout == "list" else []):
    y_top = top - i * row_h
    y_center = y_top - row_h / 2
    # Fewer episodes means taller rows: 0 at six rows, 1 at two or fewer. Taller
    # rows get bigger type and more summary lines. Rows tall enough to stack the
    # QR code under the artwork do so, giving the text the full page width;
    # otherwise text runs full width only above the QR code on the right.
    roominess = min(1, max(0, (row_h - 40 * mm) / (75 * mm)))
    qr_size = min(row_h * 0.8, 48 * mm)
    stacked = row_h >= 100 * mm
    if stacked:
        artwork_size = min(80 * mm, row_h - qr_size - 16 * mm)
        column_w = max(artwork_size, qr_size)
        group_top = y_center + (artwork_size + 5 * mm + qr_size) / 2
        artwork_x = margin + (column_w - artwork_size) / 2
        artwork_y = group_top - artwork_size
        qr_x = margin + (column_w - qr_size) / 2
        qr_y = artwork_y - 5 * mm - qr_size
        text_x = margin + column_w + 8 * mm
    else:
        artwork_size = min(row_h * 0.76, 56 * mm + roominess * 12 * mm)
        artwork_x = margin
        artwork_y = y_center - artwork_size / 2
        qr_x = W - margin - qr_size
        qr_drop = min(22 * mm, max(0, (row_h - 30 * mm) * 0.22))
        qr_y = y_center - qr_size / 2 - qr_drop
        text_x = artwork_x + artwork_size + 7 * mm

    artwork_path = artwork_for(item)
    if artwork_path:
        c.drawImage(str(artwork_path), artwork_x, artwork_y, width=artwork_size, height=artwork_size, mask="auto")
    else:
        draw_placeholder_artwork(c, artwork_x, artwork_y, artwork_size, item["show"])

    qr_img = qrcode.make(item["url"], border=4)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, kind="PNG")
    qr_buffer.seek(0)
    c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size)

    # In stacked rows nothing sits to the right of the text.
    qr_clear_y = float("-inf") if stacked else qr_y + qr_size + 3 * mm

    def width_at(baseline, font_size, x=text_x):
        """Usable line width at a baseline: full width once clear of the QR code."""
        right = W - margin if baseline - font_size * 0.3 > qr_clear_y else qr_x - 7 * mm
        return right - x

    show_font_size = 16 + roominess * 4
    show_y = artwork_y + artwork_size - show_font_size * 0.75
    line_w = width_at(show_y, show_font_size)
    date_font_size = 9 + roominess
    c.setFont("Helvetica-Oblique", date_font_size)
    date_width = c.stringWidth(item["date"], "Helvetica-Oblique", date_font_size)
    while date_width > line_w * 0.4 and date_font_size > 6.5:
        date_font_size -= 0.25
        date_width = c.stringWidth(item["date"], "Helvetica-Oblique", date_font_size)
    show_name_max_width = max(10 * mm, line_w - date_width - 4 * mm)

    # Shrink long show names before falling back to an ellipsis.
    while c.stringWidth(item["show"], "Helvetica-Bold", show_font_size) > show_name_max_width and show_font_size > 11:
        show_font_size -= 0.5
    c.setFillColor(colors.HexColor(THEME_COLORS["accent"]))
    c.setFont("Helvetica-Bold", show_font_size)
    show_name = fit_pdf_text(c, item["show"], "Helvetica-Bold", show_font_size, show_name_max_width)
    c.drawString(text_x, show_y, show_name)

    c.setFillColor(colors.HexColor(THEME_COLORS["muted"]))
    c.setFont("Helvetica-Oblique", date_font_size)
    c.drawRightString(text_x + line_w, show_y, item["date"])

    summary = str(item.get("summary") or "").strip()
    # Prefer shrinking the font and wrapping to more lines over truncating the
    # episode title with an ellipsis; the summary below has room to give.
    title_max_lines = 3 if row_h >= 55 * mm else 2
    title_max_font_size = 11 + roominess * 5
    title_y = show_y - 5.5 * mm - roominess * 2 * mm
    title_w = width_at(title_y - (title_max_lines - 1) * title_max_font_size * 1.18, title_max_font_size)
    c.setFillColor(colors.HexColor(THEME_COLORS["primary"]))
    title_lines, title_font_size = fit_title_lines(
        c, item["episode"], "Helvetica", title_max_font_size, 8, title_w, title_max_lines
    )
    c.setFont("Helvetica", title_font_size)
    title_leading = title_font_size * 1.18
    for title_line in title_lines:
        c.drawString(text_x, title_y, title_line)
        title_y -= title_leading

    row_bottom = y_top - row_h
    url_reserve_y = row_bottom + 5 * mm
    tag_text = ", ".join(" ".join(str(tag).split("_")) for tag in item.get("tags", []) if str(tag).strip())
    tag_font_size = 7.5 + roominess * 1.5
    tags_reserve_y = url_reserve_y + 4 * mm if tag_text else url_reserve_y
    content_bottom = title_y + title_leading - 1.5 * mm

    if summary:
        summary_y = content_bottom - 4 * mm - roominess * 1.5 * mm
        # Start large in roomy rows, but step down towards the six-row size
        # before cutting the summary short with an ellipsis.
        summary_font_size = 7.5 + roominess * 3
        while True:
            summary_leading = summary_font_size * 1.22
            available_lines = int((summary_y - (tags_reserve_y + 3 * mm)) / summary_leading) + 1
            max_summary_lines = max(0, min(int(12 + roominess * 18), available_lines))
            summary_lines = wrap_pdf_text(
                c, summary, "Helvetica", summary_font_size,
                lambda index: width_at(summary_y - index * summary_leading, summary_font_size),
                max_summary_lines,
            ) if max_summary_lines else []
            if (summary_lines and not summary_lines[-1].endswith("…")) or summary_font_size <= 7.5:
                break
            summary_font_size = max(7.5, summary_font_size - 0.5)
        if summary_lines:
            c.setFillColor(colors.HexColor(THEME_COLORS["summary"]))
            c.setFont("Helvetica", summary_font_size)
            for summary_line in summary_lines:
                c.drawString(text_x, summary_y, summary_line)
                summary_y -= summary_leading
            content_bottom = summary_y + summary_leading

    # Keep the tag line/URL close to the actual content instead of always
    # sitting at the bottom of the row, which leaves a large gap when a row is
    # tall (e.g. few episodes on the poster) and the summary is short.
    if tag_text:
        tags_y = max(tags_reserve_y, content_bottom - 6 * mm)
        c.setFillColor(colors.HexColor(THEME_COLORS["muted"]))
        c.setFont("Helvetica", tag_font_size)
        c.drawString(text_x, tags_y, fit_pdf_text(c, tag_text, "Helvetica", tag_font_size, width_at(tags_y, tag_font_size)))
        url_y = tags_y - 4 * mm
    else:
        url_y = max(url_reserve_y, content_bottom - 6 * mm)

    # Full-width URLs run under the artwork column, so only use that width when
    # the URL has actually dropped below the artwork's bottom edge.
    use_full_width_url = not stacked and row_h >= 55 * mm and url_y <= artwork_y - 2 * mm
    url_x = margin if use_full_width_url else text_x
    url_max_width = width_at(url_y, 8, x=url_x)
    url_font_size = 8
    while c.stringWidth(item["url"], "Helvetica", url_font_size) > url_max_width and url_font_size > 6.5:
        url_font_size -= 0.25
    visible_url = fit_pdf_text(c, item["url"], "Helvetica", url_font_size, url_max_width)
    url_width = c.stringWidth(visible_url, "Helvetica", url_font_size)
    c.setFillColor(colors.HexColor(THEME_COLORS["accent"]))
    c.setFont("Helvetica", url_font_size)
    c.drawString(url_x, url_y, visible_url)
    c.linkURL(
        item["url"],
        (url_x, url_y - 0.6 * mm, url_x + url_width, url_y + 2.4 * mm),
        relative=0,
        thickness=0,
    )

    if i < len(data) - 1:
        c.setStrokeColor(colors.HexColor(THEME_COLORS["divider"]))
        c.line(margin, y_top - row_h, W - margin, y_top - row_h)

if poster_layout == "single":
    draw_single_poster(c, data[0])

c.setFillColor(colors.HexColor(THEME_COLORS["muted"]))
c.setFont("Helvetica", 9)
c.drawCentredString(W / 2, margin / 2, edition_label)

c.save()
print(f"Wrote {output_pdf}")
if regenerate_manifest_path:
    print(f"Regenerated archived PDF from {regenerate_manifest_path} (history entry unchanged).")
elif preview_only:
    print("Preview only; not added to poster history.")
else:
    archive_pdf, archive_json = archive_generation(output_pdf, data)
    print(f"Archived {archive_pdf} and {archive_json}")

"""Turn a hand-added web link (a video, article, or podcast page) into poster details.

Details come from the provider's oEmbed endpoint when it has one (YouTube, Vimeo,
SoundCloud, Spotify, or any page that advertises oEmbed), then from the page's own
Open Graph, Twitter card, schema.org, and <title> metadata. Every source is
best-effort: a link whose page cannot be read still gets a usable entry.
"""

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

from fetch_episodes import USER_AGENT, cache_artwork_image, format_duration

MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_OEMBED_BYTES = 256 * 1024
MAX_SUMMARY_CHARS = 400
MAX_DESCRIPTION_CHARS = 2000
MAX_LINK_TAGS = 6
# Some sites (YouTube among them) send a cut-down page to unknown clients.
PAGE_USER_AGENT = "Mozilla/5.0 (compatible; PodcastPoster/1.0; +local poster studio)"

OEMBED_PROVIDERS = (
    (re.compile(r"^https?://((www|m|music)\.)?youtube\.com/|^https?://youtu\.be/", re.I), "https://www.youtube.com/oembed"),
    (re.compile(r"^https?://(www\.|player\.)?vimeo\.com/", re.I), "https://vimeo.com/api/oembed.json"),
    (re.compile(r"^https?://(www\.|m\.)?soundcloud\.com/", re.I), "https://soundcloud.com/oembed"),
    (re.compile(r"^https?://open\.spotify\.com/", re.I), "https://open.spotify.com/oembed"),
)


def http_url(value):
    if not isinstance(value, str):
        return ""
    value = value.strip()
    parts = urlsplit(value)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return ""
    return value


def site_name(url):
    host = urlsplit(url).hostname or url
    return host[4:] if host.startswith("www.") else host


def site_root(url):
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}/"


def display_date(moment):
    return f"{moment.strftime('%B')} {moment.day}, {moment.year}"


def bare_link(url, now=None):
    """The entry saved the moment a URL is added, before any details are fetched."""
    now = now or datetime.now(timezone.utc)
    return {
        "url": url,
        "show": site_name(url),
        "episode": url,
        "date": f"Added {display_date(now)}",
        "feed_url": site_root(url),
        "added_at": now.isoformat(),
        "status": "pending",
    }


def fetch_bytes(url, limit, accept="*/*"):
    request = Request(url, headers={"User-Agent": PAGE_USER_AGENT, "Accept": accept, "Accept-Language": "en"})
    with urlopen(request, timeout=15) as response:
        data = response.read(limit + 1)
        charset = response.headers.get_content_charset() or "utf-8"
        final_url = response.geturl() or url
    return data[:limit], charset, final_url


class PageMetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.tags = []
        self.title = ""
        self.oembed_url = ""
        self.json_ld = []
        self._in_title = False
        self._in_json_ld = False
        self._json_ld_text = []

    def handle_starttag(self, tag, attrs):
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "meta":
            key = (values.get("property") or values.get("name") or values.get("itemprop") or "").strip().lower()
            content = values.get("content", "").strip()
            if not key or not content:
                return
            if key in {"article:tag", "video:tag", "og:video:tag"}:
                self.tags.append(content)
            self.meta.setdefault(key, content)
        elif tag == "link":
            rel = values.get("rel", "").lower().split()
            kind = values.get("type", "").lower()
            if "alternate" in rel and kind == "application/json+oembed" and values.get("href"):
                self.oembed_url = self.oembed_url or values["href"]
        elif tag == "title":
            self._in_title = True
        elif tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_text = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self._in_json_ld = False
            try:
                self.json_ld.append(json.loads("".join(self._json_ld_text)))
            except ValueError:
                pass

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = " ".join(data.split())
        elif self._in_json_ld:
            self._json_ld_text.append(data)


def json_ld_objects(blocks):
    pending = list(blocks)
    while pending:
        item = pending.pop(0)
        if isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, dict):
            yield item
            if isinstance(item.get("@graph"), list):
                pending.extend(item["@graph"])


def first_json_ld(blocks, *keys):
    for item in json_ld_objects(blocks):
        for key in keys:
            value = item.get(key)
            if isinstance(value, dict):
                value = value.get("name")
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                value = value[0].get("name")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def parse_published(value):
    if not value:
        return None
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        try:
            moment = datetime.strptime(value[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def clean_text(value, limit):
    text = " ".join(html.unescape(value or "").split())
    if len(text) <= limit:
        return text
    cutoff = text.rfind(" ", 0, limit - 1)
    if cutoff < limit * 0.6:
        cutoff = limit - 1
    return text[:cutoff].rstrip() + "…"


def oembed_endpoint(url, discovered):
    for pattern, endpoint in OEMBED_PROVIDERS:
        if pattern.search(url):
            return f"{endpoint}?{urlencode({'url': url, 'format': 'json'})}"
    return discovered


def fetch_oembed(endpoint):
    data, charset, _ = fetch_bytes(endpoint, MAX_OEMBED_BYTES, "application/json")
    details = json.loads(data.decode(charset, errors="replace"))
    return details if isinstance(details, dict) else {}


def read_page(url):
    data, charset, final_url = fetch_bytes(url, MAX_PAGE_BYTES, "text/html,application/xhtml+xml")
    parser = PageMetadataParser()
    parser.feed(data.decode(charset, errors="replace"))
    return parser, final_url


def resolve_link(url, artwork_dir, now=None):
    """Fetch details for a link. Returns (entry, warnings); raises ValueError only for a bad URL."""
    url = http_url(url)
    if not url:
        raise ValueError("Enter a web link starting with http:// or https://.")
    entry = bare_link(url, now)
    warnings = []

    page, page_url = None, url
    try:
        page, page_url = read_page(url)
    except (OSError, URLError, ValueError) as error:
        warnings.append(f"page: {error}")

    oembed = {}
    endpoint = oembed_endpoint(url, urljoin(page_url, page.oembed_url) if page and page.oembed_url else "")
    if endpoint:
        try:
            oembed = fetch_oembed(endpoint)
        except (OSError, URLError, ValueError) as error:
            warnings.append(f"oEmbed: {error}")

    meta = page.meta if page else {}
    blocks = page.json_ld if page else []

    def text(*values):
        return next((value.strip() for value in values if isinstance(value, str) and value.strip()), "")

    title = text(oembed.get("title"), meta.get("og:title"), meta.get("twitter:title"), first_json_ld(blocks, "headline", "name"), page.title if page else "")
    show = text(oembed.get("author_name"), first_json_ld(blocks, "author", "creator", "publisher"), meta.get("og:site_name"), oembed.get("provider_name"))
    description = text(meta.get("og:description"), meta.get("twitter:description"), meta.get("description"), first_json_ld(blocks, "description"))
    published = parse_published(text(
        first_json_ld(blocks, "datePublished", "uploadDate"),
        meta.get("datepublished"),
        meta.get("uploaddate"),
        meta.get("article:published_time"),
        meta.get("og:video:release_date"),
    ))
    duration = format_duration(text(first_json_ld(blocks, "duration"), meta.get("duration"), meta.get("video:duration"), str(oembed.get("duration") or "")))
    image_url = text(meta.get("og:image"), meta.get("og:image:url"), meta.get("twitter:image"), oembed.get("thumbnail_url"))
    author_url = http_url(oembed.get("author_url"))

    if title:
        entry["episode"] = clean_text(title, 300)
    if show:
        entry["show"] = clean_text(show, 120)
    if author_url:
        entry["feed_url"] = author_url
    if description:
        entry["description"] = clean_text(description, MAX_DESCRIPTION_CHARS)
        entry["summary"] = clean_text(description, MAX_SUMMARY_CHARS)
    if published and published <= (now or datetime.now(timezone.utc)):
        entry["date"] = display_date(published)
        entry["published_at"] = published.isoformat()
    if duration:
        entry["duration"] = duration
    tags = []
    for tag in page.tags if page else []:
        tag = " ".join(tag.lstrip("#").split())[:40]
        if tag and tag.casefold() not in {existing.casefold() for existing in tags}:
            tags.append(tag)
    if tags:
        entry["tags"] = tags[:MAX_LINK_TAGS]

    if image_url:
        image_url = urljoin(page_url, image_url)
        digest = hashlib.sha256(image_url.encode()).hexdigest()
        artwork_path, status = cache_artwork_image(image_url, artwork_dir / f"link-{digest}-v2.png")
        if artwork_path:
            entry["artwork_path"] = artwork_path
        else:
            warnings.append("artwork: image could not be downloaded")

    found_details = bool(title or oembed)
    entry["status"] = "ready" if found_details else "failed"
    if not found_details:
        entry["error"] = "; ".join(warnings) or "No title or preview details found on the page."
    return entry, warnings

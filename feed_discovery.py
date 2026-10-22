"""Find the feed behind a pasted link so it can be added as a subscription.

Accepts a feed URL itself, a YouTube channel, @handle, playlist, or video link
(YouTube publishes an Atom feed of each channel's and playlist's latest ~15
videos), an Apple Podcasts page, or any website that advertises its feed with
<link rel="alternate">.
"""

import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import parse_qs, urljoin, urlsplit

from link_preview import fetch_bytes, http_url

MAX_FEED_BYTES = 8 * 1024 * 1024
FEED_TYPES = {"application/rss+xml", "application/atom+xml", "application/feed+json", "application/xml", "text/xml"}
YOUTUBE_HOST = re.compile(r"^((www|m|music)\.)?youtube\.com$|^youtu\.be$", re.I)
YOUTUBE_CHANNEL_ID = re.compile(r"^UC[\w-]{22}$")
YOUTUBE_FEED = "https://www.youtube.com/feeds/videos.xml"


class FeedLinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.feeds = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "link":
            rel = values.get("rel", "").lower().split()
            kind = values.get("type", "").lower()
            if "alternate" in rel and kind in FEED_TYPES and values.get("href"):
                self.feeds.append((values["href"], values.get("title", "")))
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = " ".join(data.split())


def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


def feed_title(data):
    """Return the feed's title, or None when the data is not an RSS or Atom feed."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    if local_name(root.tag) not in {"rss", "feed", "rdf"}:
        return None
    channel = next((node for node in root.iter() if local_name(node.tag) == "channel"), root)
    title = next(((node.text or "").strip() for node in channel if local_name(node.tag) == "title"), "")
    return " ".join(title.split())


def youtube_feed_from_url(url):
    """A YouTube feed URL that can be built from the link alone, if any."""
    parts = urlsplit(url)
    if not YOUTUBE_HOST.match(parts.hostname or ""):
        return ""
    query = parse_qs(parts.query)
    if parts.path.rstrip("/") == "/feeds/videos.xml":
        return url
    playlist = query.get("list", [""])[0]
    if parts.path.rstrip("/") == "/playlist" and playlist:
        return f"{YOUTUBE_FEED}?playlist_id={playlist}"
    match = re.match(r"^/channel/(UC[\w-]{22})", parts.path)
    if match:
        return f"{YOUTUBE_FEED}?channel_id={match.group(1)}"
    return ""


def youtube_channel_id_from_page(page):
    """Channel and video pages name their channel; @handle pages need this lookup."""
    for pattern in (
        r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"',
        r'"externalId":"(UC[\w-]{22})"',
        r'"channelId":"(UC[\w-]{22})"',
        r'itemprop="(?:identifier|channelId)" content="(UC[\w-]{22})"',
    ):
        match = re.search(pattern, page)
        if match:
            return match.group(1)
    return ""


def apple_podcasts_feed(url):
    parts = urlsplit(url)
    if (parts.hostname or "").lower() not in {"podcasts.apple.com", "itunes.apple.com"}:
        return ""
    match = re.search(r"/id(\d+)", parts.path)
    if not match:
        return ""
    data, charset, _ = fetch_bytes(f"https://itunes.apple.com/lookup?id={match.group(1)}&entity=podcast", 256 * 1024, "application/json")
    results = json.loads(data.decode(charset, errors="replace")).get("results", [])
    return next((http_url(item.get("feedUrl")) for item in results if http_url(item.get("feedUrl"))), "")


def read_feed(feed_url):
    data, _, final_url = fetch_bytes(feed_url, MAX_FEED_BYTES, "application/rss+xml, application/atom+xml, application/xml, text/xml")
    title = feed_title(data)
    if title is None:
        raise ValueError(f"{feed_url} did not return an RSS or Atom feed.")
    return title


def discover_feed(url):
    """Return {"feed_url", "title"} for a pasted link; raise ValueError when none is found."""
    url = http_url(url)
    if not url:
        raise ValueError("Enter a web link starting with http:// or https://.")
    try:
        feed_url = youtube_feed_from_url(url) or apple_podcasts_feed(url)
        if not feed_url:
            data, charset, final_url = fetch_bytes(url, MAX_FEED_BYTES, "application/rss+xml, application/atom+xml, text/html;q=0.9, */*;q=0.8")
            title = feed_title(data)
            if title is not None:
                return {"feed_url": url, "title": title or (urlsplit(url).hostname or url)}
            page = data.decode(charset, errors="replace")
            if YOUTUBE_HOST.match(urlsplit(final_url).hostname or ""):
                channel_id = youtube_channel_id_from_page(page)
                if channel_id:
                    feed_url = f"{YOUTUBE_FEED}?channel_id={channel_id}"
            if not feed_url:
                parser = FeedLinkParser()
                parser.feed(page)
                if parser.feeds:
                    # Prefer a feed that is not the site's comments feed.
                    href = next((href for href, title in parser.feeds if "comment" not in (title + href).lower()), parser.feeds[0][0])
                    feed_url = urljoin(final_url, href)
        if not feed_url:
            raise ValueError("No podcast or video feed was found at that link. Try the show's feed URL or its website.")
        title = read_feed(feed_url)
    except (OSError, URLError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read that link: {error}") from error
    return {"feed_url": feed_url, "title": title or (urlsplit(feed_url).hostname or feed_url)}

"""Work out what a pasted link is: a feed to follow, a single item to add, or both.

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

from fetch_episodes import feed_media_type, is_video_url
from link_preview import PageMetadataParser, fetch_bytes, fetch_oembed, http_url, oembed_endpoint, site_name, youtube_video_id

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


def feed_info(data, feed_url):
    """(title, media type) when the data is an RSS or Atom feed, else None."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    if local_name(root.tag) not in {"rss", "feed", "rdf"}:
        return None
    channel = next((node for node in root.iter() if local_name(node.tag) == "channel"), root)
    title = next(((node.text or "").strip() for node in channel if local_name(node.tag) == "title"), "")
    return " ".join(title.split()), feed_media_type(root, feed_url)


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


def youtube_page_title(url):
    try:
        data, charset, _ = fetch_bytes(url, MAX_FEED_BYTES, "text/html")
    except (OSError, URLError, ValueError):
        return ""
    metadata = PageMetadataParser()
    metadata.feed(data.decode(charset, errors="replace"))
    return metadata.meta.get("og:title") or metadata.title.removesuffix(" - YouTube")


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
    """(title, media type) of a feed; ValueError when the URL is not a feed."""
    data, _, final_url = fetch_bytes(feed_url, MAX_FEED_BYTES, "application/rss+xml, application/atom+xml, application/xml, text/xml")
    info = feed_info(data, feed_url)
    if info is None:
        raise ValueError(f"{feed_url} did not return an RSS or Atom feed.")
    return info


def feed_in_page(page, page_url):
    """The feed a web page advertises, preferring one that is not a comments feed."""
    parser = FeedLinkParser()
    parser.feed(page)
    if not parser.feeds:
        return ""
    href = next((href for href, title in parser.feeds if "comment" not in (title + href).lower()), parser.feeds[0][0])
    return urljoin(page_url, href)


def discover_feed(url):
    """Return {"feed_url", "title", "media"} for a pasted link; raise ValueError when none is found."""
    url = http_url(url)
    if not url:
        raise ValueError("Enter a web link starting with http:// or https://.")
    page_title = ""
    try:
        feed_url = youtube_feed_from_url(url) or apple_podcasts_feed(url)
        if not feed_url:
            data, charset, final_url = fetch_bytes(url, MAX_FEED_BYTES, "application/rss+xml, application/atom+xml, text/html;q=0.9, */*;q=0.8")
            info = feed_info(data, url)
            if info is not None:
                return {"feed_url": url, "title": info[0] or (urlsplit(url).hostname or url), "media": info[1]}
            page = data.decode(charset, errors="replace")
            if YOUTUBE_HOST.match(urlsplit(final_url).hostname or ""):
                channel_id = youtube_channel_id_from_page(page)
                if channel_id:
                    feed_url = f"{YOUTUBE_FEED}?channel_id={channel_id}"
                    metadata = PageMetadataParser()
                    metadata.feed(page)
                    page_title = metadata.meta.get("og:title") or metadata.title.removesuffix(" - YouTube")
            feed_url = feed_url or feed_in_page(page, final_url)
        if not feed_url:
            raise ValueError("No podcast, video, or blog feed was found at that link. Try the show's feed URL or its website.")
        try:
            title, media = read_feed(feed_url)
        except (OSError, URLError, ValueError):
            # YouTube's feeds drop out for hours at a time while the channel is fine. A
            # feed URL built from a real channel ID is right regardless; scans retry it.
            if not feed_url.startswith(YOUTUBE_FEED):
                raise
            if not page_title and feed_url != url:
                page_title = youtube_page_title(url)
            title, media = page_title or parse_qs(urlsplit(feed_url).query).get("channel_id", ["YouTube channel"])[0], "video"
    except (OSError, URLError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read that link: {error}") from error
    return {"feed_url": feed_url, "title": title or (urlsplit(feed_url).hostname or feed_url), "media": media}


def guess_item_media(url, page_meta=None):
    """Media type for a single pasted item, before its details are fetched."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if is_video_url(url):
        return "video"
    if host == "open.spotify.com" and parts.path.startswith("/episode/"):
        return "podcast"
    if host in {"podcasts.apple.com", "itunes.apple.com"} or host.endswith("soundcloud.com"):
        return "podcast"
    meta = page_meta or {}
    kind = meta.get("og:type", "").lower()
    if kind.startswith("video") or meta.get("og:video") or meta.get("og:video:url"):
        return "video"
    if meta.get("og:audio") or "podcast" in kind or kind.startswith("music"):
        return "podcast"
    return "article"


def inspect_link(url):
    """Work out what a pasted link is, for the + Add preview.

    Returns {"url", "item", "follow", "default", "error"}: "item" describes adding
    this one page (media type and a title when known) and "follow" describes
    subscribing to a feed (feed URL, title, media type). Either may be None; the
    default is what the link most likely means. A YouTube video offers its
    channel to follow too, and an article offers its site's feed.
    """
    url = http_url(url)
    result = {"url": url, "item": None, "follow": None, "default": "item", "error": ""}
    if not url:
        result["error"] = "Not a web link; links start with http:// or https://."
        return result
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    query = parse_qs(parts.query)
    try:
        if YOUTUBE_HOST.match(host):
            if youtube_video_id(url):
                result["item"] = {"media": "video", "title": ""}
                try:
                    details = fetch_oembed(oembed_endpoint(url, ""))
                    result["item"]["title"] = str(details.get("title") or "")
                    channel = http_url(details.get("author_url"))
                    if channel:
                        result["follow"] = {"url": channel, "title": str(details.get("author_name") or channel), "media": "video"}
                except (OSError, URLError, ValueError):
                    pass
                return result
            found = discover_feed(url)
            result["follow"] = {"url": found["feed_url"], **found}
            result["default"] = "follow"
            return result
        if host in {"podcasts.apple.com", "itunes.apple.com"} and query.get("i"):
            result["item"] = {"media": "podcast", "title": ""}
            show = url.split("?", 1)[0]
            try:
                found = discover_feed(show)
                result["follow"] = {"url": found["feed_url"], **found}
            except ValueError:
                pass
            return result
        if host == "open.spotify.com":
            if parts.path.startswith("/show/"):
                result["error"] = "Spotify doesn't publish a feed for its shows. Add single episodes, or follow the show's own website or RSS feed."
                return result
            result["item"] = {"media": "podcast", "title": ""}
            return result
        if is_video_url(url) or (host.endswith("soundcloud.com") and len([part for part in parts.path.split("/") if part]) >= 2):
            result["item"] = {"media": guess_item_media(url), "title": ""}
            return result
        if host in {"podcasts.apple.com", "itunes.apple.com"}:
            found = discover_feed(url)
            result["follow"] = {"url": found["feed_url"], **found}
            result["default"] = "follow"
            return result

        data, charset, final_url = fetch_bytes(url, MAX_FEED_BYTES, "application/rss+xml, application/atom+xml, text/html;q=0.9, */*;q=0.8")
        info = feed_info(data, url)
        if info is not None:
            result["follow"] = {"url": url, "feed_url": url, "title": info[0] or site_name(url), "media": info[1]}
            result["default"] = "follow"
            return result
        page = PageMetadataParser()
        page.feed(data.decode(charset, errors="replace"))
        title = page.meta.get("og:title") or page.title
        result["item"] = {"media": guess_item_media(final_url, page.meta), "title": title}
        feed_url = feed_in_page(data.decode(charset, errors="replace"), final_url)
        if feed_url:
            try:
                feed_title, media = read_feed(feed_url)
                result["follow"] = {"url": feed_url, "feed_url": feed_url, "title": feed_title or site_name(url), "media": media}
            except (OSError, URLError, ValueError):
                pass
        # A site's home page means "follow this site"; any deeper page is one item.
        if result["follow"] and urlsplit(final_url).path.strip("/") == "":
            result["default"] = "follow"
    except ValueError as error:
        result["error"] = str(error)
    except (OSError, URLError, json.JSONDecodeError) as error:
        result["error"] = f"Could not read that link: {error}"
    return result

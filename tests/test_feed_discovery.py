import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import feed_discovery
import server

CHANNEL_ID = "UCabcdefghijklmnopqrstuv"
YOUTUBE_FEED = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
YOUTUBE_ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Not Just Bikes</title></feed>"""
PODCAST_RSS = b"""<?xml version="1.0"?><rss><channel><title>  Example   Podcast </title>
<item><title>One</title><enclosure url="https://example.test/one.mp3" type="audio/mpeg"/></item></channel></rss>"""
BLOG_ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>A Blog</title>
<entry><title>Post</title><link href="https://blog.example/post"/></entry></feed>"""


def fake_fetch(responses):
    def fetch(url, limit, accept="*/*"):
        if url not in responses:
            raise URLError(f"unexpected fetch {url}")
        body = responses[url]
        data = json.dumps(body).encode() if isinstance(body, dict) else body
        return data, "utf-8", url
    return fetch


class FeedDiscoveryTests(unittest.TestCase):
    def discover(self, url, responses):
        with patch.object(feed_discovery, "fetch_bytes", side_effect=fake_fetch(responses)):
            return feed_discovery.discover_feed(url)

    def test_feed_url_is_used_as_is(self):
        found = self.discover("https://example.test/feed.xml", {"https://example.test/feed.xml": PODCAST_RSS})
        self.assertEqual(found, {"feed_url": "https://example.test/feed.xml", "title": "Example Podcast", "media": "podcast"})

    def test_youtube_channel_and_playlist_links_map_straight_to_feeds(self):
        found = self.discover(f"https://www.youtube.com/channel/{CHANNEL_ID}/videos", {YOUTUBE_FEED: YOUTUBE_ATOM})
        self.assertEqual(found, {"feed_url": YOUTUBE_FEED, "title": "Not Just Bikes", "media": "video"})
        self.assertEqual(
            feed_discovery.youtube_feed_from_url("https://www.youtube.com/playlist?list=PL123"),
            "https://www.youtube.com/feeds/videos.xml?playlist_id=PL123",
        )

    def test_youtube_handle_page_is_read_for_its_channel_id(self):
        page = f'<html><head><link rel="canonical" href="https://www.youtube.com/channel/{CHANNEL_ID}"></head></html>'.encode()
        found = self.discover("https://www.youtube.com/@NotJustBikes", {
            "https://www.youtube.com/@NotJustBikes": page,
            YOUTUBE_FEED: YOUTUBE_ATOM,
        })
        self.assertEqual(found["feed_url"], YOUTUBE_FEED)

    def test_website_advertising_a_feed_is_followed_and_comment_feeds_skipped(self):
        page = b"""<html><head>
        <link rel="alternate" type="application/rss+xml" title="Comments Feed" href="/comments/feed">
        <link rel="alternate" type="application/rss+xml" title="Episodes" href="/feed/podcast">
        </head></html>"""
        found = self.discover("https://show.example/", {
            "https://show.example/": page,
            "https://show.example/feed/podcast": PODCAST_RSS,
        })
        self.assertEqual(found["feed_url"], "https://show.example/feed/podcast")

    def test_apple_podcasts_page_uses_the_itunes_lookup(self):
        found = self.discover("https://podcasts.apple.com/au/podcast/example/id12345", {
            "https://itunes.apple.com/lookup?id=12345&entity=podcast": {"results": [{"feedUrl": "https://example.test/feed.xml"}]},
            "https://example.test/feed.xml": PODCAST_RSS,
        })
        self.assertEqual(found["feed_url"], "https://example.test/feed.xml")

    def test_page_without_a_feed_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "No podcast, video, or blog feed"):
            self.discover("https://plain.example/", {"https://plain.example/": b"<html><title>Plain</title></html>"})
        with self.assertRaisesRegex(ValueError, "Could not read"):
            self.discover("https://down.example/", {})


class AddSubscriptionTests(unittest.TestCase):
    def test_subscribing_adds_one_outline_and_ignores_repeats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "user-data" / "config.json"
            config_path.parent.mkdir()
            config_path.write_text(json.dumps({"opml_path": "user-data/subscriptions.opml", "slots": []}), encoding="utf-8")
            found = {"feed_url": YOUTUBE_FEED, "title": "Not Just Bikes"}
            with (
                patch.object(server, "CONFIG_PATH", config_path),
                patch.object(server, "BASE_DIR", root),
                patch.object(feed_discovery, "discover_feed", return_value=found),
            ):
                first = server.add_subscription("https://www.youtube.com/@NotJustBikes")
                again = server.add_subscription("https://www.youtube.com/@NotJustBikes")
                subscriptions = server.list_opml_subscriptions((root / "user-data" / "subscriptions.opml").read_bytes())

        self.assertTrue(first["added"])
        self.assertFalse(again["added"])
        self.assertEqual(again["feeds"], 1)
        self.assertEqual(subscriptions, [{"title": "Not Just Bikes", "url": YOUTUBE_FEED, "groups": []}])


if __name__ == "__main__":
    unittest.main()

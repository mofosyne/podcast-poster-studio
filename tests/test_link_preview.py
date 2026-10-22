import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import link_preview
import server

NOW = datetime(2026, 10, 22, 9, 30, tzinfo=timezone.utc)

YOUTUBE_PAGE = b"""<!doctype html><html><head>
<title>A video - YouTube</title>
<meta property="og:title" content="Page title loses to oEmbed">
<meta property="og:image" content="https://i.ytimg.com/vi/abc123/maxresdefault.jpg">
<meta property="og:description" content="Why trains are great &amp; how to build them.">
<meta itemprop="datePublished" content="2026-01-02T03:04:05-08:00">
<meta itemprop="duration" content="PT12M30S">
<meta property="og:video:tag" content="Trains">
<meta property="og:video:tag" content="#urbanism">
<meta property="og:video:tag" content="trains">
</head><body></body></html>"""

YOUTUBE_OEMBED = {
    "title": "A video about trains",
    "author_name": "Not Just Bikes",
    "author_url": "https://www.youtube.com/@NotJustBikes",
    "thumbnail_url": "https://i.ytimg.com/vi/abc123/hqdefault.jpg",
    "provider_name": "YouTube",
}

ARTICLE_PAGE = b"""<html><head>
<title>Fallback title</title>
<link rel="alternate" type="application/json+oembed" href="/oembed?id=7">
<meta name="description" content="Plain meta description.">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
  {"@type":"NewsArticle","headline":"Rivers are back","datePublished":"2025-05-06",
   "author":[{"@type":"Person","name":"A. Writer"}]}]}</script>
<meta property="og:image" content="/images/river.jpg">
</head></html>"""


def fake_fetch(responses):
    def fetch(url, limit, accept="*/*"):
        for prefix, body in responses.items():
            if url.startswith(prefix):
                if isinstance(body, Exception):
                    raise body
                data = json.dumps(body).encode() if isinstance(body, dict) else body
                return data, "utf-8", url
        raise URLError(f"unexpected fetch {url}")
    return fetch


class LinkPreviewTests(unittest.TestCase):
    def resolve(self, url, responses):
        cached = []

        def cache(image_url, cache_path):
            cached.append(image_url)
            return cache_path, "downloaded"

        with (
            patch.object(link_preview, "fetch_bytes", side_effect=fake_fetch(responses)),
            patch.object(link_preview, "cache_artwork_image", side_effect=cache),
        ):
            entry, warnings = link_preview.resolve_link(url, Path("/cache/artwork"), NOW)
        return entry, warnings, cached

    def test_youtube_link_combines_oembed_with_page_metadata(self):
        url = "https://www.youtube.com/watch?v=abc123"
        entry, warnings, cached = self.resolve(url, {
            "https://www.youtube.com/watch": YOUTUBE_PAGE,
            "https://www.youtube.com/oembed?": YOUTUBE_OEMBED,
        })

        self.assertEqual(entry["status"], "ready")
        self.assertEqual(entry["url"], url)
        self.assertEqual(entry["episode"], "A video about trains")
        self.assertEqual(entry["show"], "Not Just Bikes")
        self.assertEqual(entry["feed_url"], "https://www.youtube.com/@NotJustBikes")
        self.assertEqual(entry["summary"], "Why trains are great & how to build them.")
        self.assertEqual(entry["date"], "January 2, 2026")
        self.assertEqual(entry["duration"], "12 min")
        self.assertEqual(entry["tags"], ["Trains", "urbanism"])
        # The page's own image is tried first and used when it downloads.
        self.assertEqual(cached, ["https://i.ytimg.com/vi/abc123/maxresdefault.jpg"])
        self.assertTrue(entry["artwork_path"].name.startswith("link-"))
        self.assertEqual(warnings, [])

    def test_youtube_without_page_prefers_full_size_thumbnail_over_letterboxed_one(self):
        url = "https://youtu.be/abcdefghijk"
        attempts = []

        def cache(image_url, cache_path):
            attempts.append(image_url)
            return (None, "unavailable") if "maxresdefault" in image_url else (cache_path, "downloaded")

        with (
            patch.object(link_preview, "fetch_bytes", side_effect=fake_fetch({
                "https://youtu.be/": URLError("HTTP Error 429"),
                "https://www.youtube.com/oembed?": YOUTUBE_OEMBED,
            })),
            patch.object(link_preview, "cache_artwork_image", side_effect=cache),
        ):
            entry, _ = link_preview.resolve_link(url, Path("/cache/artwork"), NOW)

        self.assertEqual(entry["status"], "ready")
        self.assertEqual(attempts, [
            "https://i.ytimg.com/vi/abcdefghijk/maxresdefault.jpg",
            "https://i.ytimg.com/vi/abc123/hqdefault.jpg",
        ])
        self.assertIn("artwork_path", entry)
        self.assertEqual(link_preview.youtube_video_id("https://www.youtube.com/shorts/abcdefghijk?feature=share"), "abcdefghijk")
        self.assertEqual(link_preview.youtube_video_id("https://example.com/watch?v=abcdefghijk"), "")

    def test_youtube_short_links_use_the_youtube_oembed_endpoint(self):
        endpoint = link_preview.oembed_endpoint("https://youtu.be/abc123", "")
        self.assertTrue(endpoint.startswith("https://www.youtube.com/oembed?"))
        self.assertIn("url=https%3A%2F%2Fyoutu.be%2Fabc123", endpoint)

    def test_article_uses_discovered_oembed_and_json_ld(self):
        entry, _, cached = self.resolve("https://news.example/rivers", {
            "https://news.example/rivers": ARTICLE_PAGE,
            "https://news.example/oembed?id=7": {"provider_name": "Example News"},
        })

        self.assertEqual(entry["episode"], "Rivers are back")
        self.assertEqual(entry["show"], "A. Writer")
        self.assertEqual(entry["summary"], "Plain meta description.")
        self.assertEqual(entry["date"], "May 6, 2025")
        self.assertEqual(entry["feed_url"], "https://news.example/")
        self.assertEqual(cached, ["https://news.example/images/river.jpg"])

    def test_unreachable_page_keeps_a_bare_entry_marked_failed(self):
        entry, warnings, _ = self.resolve("https://www.example.com/missing", {
            "https://www.example.com/": URLError("offline"),
        })

        self.assertEqual(entry["status"], "failed")
        self.assertEqual(entry["show"], "example.com")
        self.assertEqual(entry["episode"], "https://www.example.com/missing")
        self.assertEqual(entry["date"], "Added October 22, 2026")
        self.assertIn("offline", entry["error"])
        self.assertTrue(warnings)

    def test_rejects_non_web_links(self):
        for url in ("ftp://example.com/file", "example.com", "javascript:alert(1)", ""):
            with self.subTest(url=url), self.assertRaises(ValueError):
                link_preview.resolve_link(url, Path("/tmp"), NOW)


class LinkStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.config_path = root / "user-data" / "config.json"
        self.config_path.parent.mkdir()
        self.config_path.write_text(json.dumps({"poster_layout": "list", "slots": []}), encoding="utf-8")
        self.artwork = root / "user-data" / "cache" / "artwork" / "link-abc-v2.png"
        self.artwork.parent.mkdir(parents=True)
        self.artwork.write_bytes(b"png")
        self.patches = [
            patch.object(server, "CONFIG_PATH", self.config_path),
            patch.object(server, "USER_DATA_DIR", root / "user-data"),
            patch.object(server, "BASE_DIR", root),
        ]
        for active in self.patches:
            active.start()

    def tearDown(self):
        for active in reversed(self.patches):
            active.stop()
        self.directory.cleanup()

    def resolved(self, url, **changes):
        entry = {
            **link_preview.bare_link(url, NOW),
            "status": "ready",
            "show": "Not Just Bikes",
            "episode": "A video about trains",
            "date": "January 2, 2026",
            "published_at": "2026-01-02T11:04:05+00:00",
            "feed_url": "https://www.youtube.com/@NotJustBikes",
            "summary": "Why trains are great.",
            "artwork_path": self.artwork,
        }
        entry.update(changes)
        return entry, []

    def test_bare_links_are_saved_immediately_and_deduplicated(self):
        result = server.add_links({"text": "https://a.example/one\nhttps://b.example/two  https://a.example/one"})
        again = server.add_links({"urls": ["https://a.example/one"]})

        self.assertEqual(result["added"], ["https://a.example/one", "https://b.example/two"])
        self.assertEqual(again["added"], [])
        links = server.get_links()
        self.assertEqual([link["status"] for link in links], ["pending", "pending"])
        self.assertEqual(links[0]["show"], "a.example")
        self.assertEqual(links[0]["episode"], "https://a.example/one")
        with self.assertRaises(ValueError):
            server.add_links({"text": "https://ok.example not-a-link"})

    def test_a_bare_link_can_be_shortlisted_and_picked_before_details_arrive(self):
        url = "https://www.youtube.com/watch?v=abc123"
        server.add_links({"urls": [url]})
        bare = server.get_links()[0]
        copy = {key: bare[key] for key in ("show", "episode", "date", "url", "feed_url")}
        server.add_to_shortlist(copy)
        server.add_to_draft({**copy, "type": "fixed"})
        server.update_draft_slot(url, {"summary": "My own words."})

        with patch.object(link_preview, "resolve_link", return_value=self.resolved(url)):
            result = server.fetch_link_details(url)

        self.assertTrue(result["shortlist_changed"])
        self.assertTrue(result["draft_changed"])
        link = server.get_links()[0]
        self.assertEqual(link["status"], "ready")
        self.assertEqual(link["artwork_path"], "user-data/cache/artwork/link-abc-v2.png")
        self.assertEqual(link["added_at"], bare["added_at"])
        shortlisted = server.get_shortlist()[0]
        self.assertEqual(shortlisted["episode"], "A video about trains")
        self.assertEqual(shortlisted["summary"], "Why trains are great.")
        slot = server.get_draft_slots(server.load_config())[0]
        self.assertEqual(slot["show"], "Not Just Bikes")
        self.assertEqual(slot["date"], "January 2, 2026")
        self.assertEqual(slot["artwork_path"], "user-data/cache/artwork/link-abc-v2.png")
        # The summary typed before the fetch finished is kept.
        self.assertEqual(slot["summary"], "My own words.")
        server.validate_slots([slot])

    def test_failed_fetch_keeps_the_link_and_records_the_error(self):
        url = "https://offline.example/page"
        server.add_links({"urls": [url]})
        failed = {**link_preview.bare_link(url, NOW), "status": "failed", "error": "page: offline"}

        with patch.object(link_preview, "resolve_link", return_value=(failed, ["page: offline"])):
            result = server.fetch_link_details(url)

        self.assertEqual(result["link"]["status"], "failed")
        self.assertEqual(result["link"]["error"], "page: offline")
        self.assertEqual(server.get_links()[0]["episode"], url)

    def test_undated_link_keeps_its_added_date(self):
        url = "https://blog.example/post"
        server.add_links({"urls": [url]})
        added_date = server.get_links()[0]["date"]
        entry, _ = self.resolved(url, date="Added January 1, 2030")
        entry.pop("published_at")

        with patch.object(link_preview, "resolve_link", return_value=(entry, [])):
            server.fetch_link_details(url)

        self.assertEqual(server.get_links()[0]["date"], added_date)

    def test_remove_link_leaves_shortlist_copy(self):
        url = "https://a.example/one"
        server.add_links({"urls": [url]})
        bare = server.get_links()[0]
        server.add_to_shortlist({key: bare[key] for key in ("show", "episode", "date", "url", "feed_url")})

        self.assertEqual(server.remove_link(url), [])
        self.assertEqual(len(server.get_shortlist()), 1)
        with self.assertRaises(ValueError):
            server.remove_link(url)
        with self.assertRaises(ValueError):
            server.fetch_link_details(url)


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import link_preview

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


if __name__ == "__main__":
    unittest.main()

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from fetch_episodes import (
    episode_title_key,
    episode_url_key,
    load_posted_history,
    parse_feed,
    read_opml,
    render_page,
    scan_feed,
)


NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)

FEED_URL = "https://example.test/podcast.xml"


class EpisodeParsingTests(unittest.TestCase):
    def test_rss_entries_are_parsed_without_a_recency_cutoff(self):
        feed = b"""<?xml version='1.0'?>
        <rss version='2.0'><channel>
          <item><title>New episode</title><link>https://example.test/new</link>
            <pubDate>Mon, 12 Oct 2026 10:00:00 GMT</pubDate></item>
          <item><title>Old episode</title><link>https://example.test/old</link>
            <pubDate>Tue, 1 Sep 2026 10:00:00 GMT</pubDate></item>
          <item><title>Unsafe link</title><link>javascript:alert(1)</link>
            <pubDate>Mon, 12 Oct 2026 11:00:00 GMT</pubDate></item>
        </channel></rss>"""

        episodes = parse_feed(feed, "Example Show", FEED_URL, NOW)

        self.assertEqual([episode["episode"] for episode in episodes], ["New episode", "Old episode"])
        self.assertEqual(episodes[0]["date"], "October 12, 2026")
        self.assertEqual(episodes[0]["feed_url"], FEED_URL)

    def test_atom_relative_links_and_iso_dates(self):
        feed = b"""<?xml version='1.0'?>
        <feed xmlns='http://www.w3.org/2005/Atom'>
          <entry><title>Atom episode</title><link href='/episodes/42'/>
            <published>2026-10-12T12:30:00Z</published></entry>
        </feed>"""

        episodes = parse_feed(feed, "Atom Show", FEED_URL, NOW)

        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["url"], "https://example.test/episodes/42")
        self.assertEqual(episodes[0]["episode"], "Atom episode")

    def test_opml_reads_nested_feeds_and_deduplicates_urls(self):
        opml = """<opml><body><outline text='Folder'>
          <outline text='Example Show' xmlUrl='https://example.test/feed.xml'/>
          <outline text='Duplicate' xmlUrl='https://example.test/feed.xml'/>
          <outline text='Unsafe' xmlUrl='javascript:alert(1)'/>
        </outline></body></opml>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feeds.opml"
            path.write_text(opml, encoding="utf-8")

            feeds = read_opml(path)

        self.assertEqual(feeds, [("Example Show", "https://example.test/feed.xml")])

    def test_cached_feed_is_used_when_request_fails(self):
        feed = b"""<rss><channel><item><title>Cached episode</title>
        <link>https://example.test/cached</link>
        <pubDate>Mon, 12 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>"""
        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            cached_path = cache_dir / f"{hashlib.sha256(FEED_URL.encode()).hexdigest()}.xml"
            cached_path.write_bytes(feed)

            with patch("fetch_episodes.urlopen", side_effect=URLError("offline")):
                episodes, status, error = scan_feed("Example Show", FEED_URL, cache_dir, NOW)

        self.assertEqual(status, "cached")
        self.assertIn("offline", error or "")
        self.assertEqual(episodes[0]["episode"], "Cached episode")

    def test_history_indexes_poster_slots_by_url_and_title(self):
        with tempfile.TemporaryDirectory() as directory:
            history_dir = Path(directory)
            manifest = {
                "generated_at": "2026-10-01T10:00:00+00:00",
                "edition": "OCTOBER 2026",
                "pdf": "poster-20261001.pdf",
                "slots": [{
                    "show": "Example Show",
                    "episode": "Old episode",
                    "url": "https://example.test/old",
                }],
            }
            (history_dir / "poster-20261001.json").write_text(json.dumps(manifest), encoding="utf-8")

            history = load_posted_history(history_dir)

        self.assertEqual(history[episode_url_key("https://example.test/old/")]["edition"], "OCTOBER 2026")
        self.assertEqual(history[episode_title_key("Example Show", "Old episode")]["pdf"], "poster-20261001.pdf")

    def test_candidate_html_escapes_script_closing_text(self):
        episode = {
            "show": "Example",
            "episode": "</script><script>alert(1)</script>",
            "date": "October 12, 2026",
            "published_at": "2026-10-12T10:00:00+00:00",
            "url": "https://example.test/episode",
            "feed_url": FEED_URL,
            "previously_posted": {"edition": "OCTOBER 2026", "generated_at": "2026-10-01"},
        }

        page = render_page([episode], 1, 0, 0, "October 13, 2026")

        self.assertNotIn("</script><script>alert(1)", page)
        self.assertIn("\\u003c/script>", page)
        self.assertIn("Previously posted", page)
        self.assertIn("1 previously posted", page)


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from xml.etree import ElementTree as ET

from PIL import Image

from fetch_episodes import (
    cache_artwork_image,
    cache_feed_artwork,
    episode_description,
    episode_title_key,
    episode_url_key,
    latest_episode_artwork_sources,
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
          <title>Example Show</title>
          <description><![CDATA[<p>A thoughtful channel description.</p>]]></description>
          <image><url>https://example.test/cover.png</url></image>
          <item><title>New episode</title><link>https://example.test/new</link>
            <description>&lt;p&gt;A useful episode summary.&lt;/p&gt;&lt;script&gt;unsafe()&lt;/script&gt;</description>
            <duration>1500</duration>
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
        self.assertEqual(episodes[0]["artwork_url"], "https://example.test/cover.png")
        self.assertEqual(episodes[0]["description"], "A useful episode summary.")
        self.assertEqual(episodes[0]["duration"], "25 min")
        self.assertEqual(episodes[0]["feed_description"], "A thoughtful channel description.")
        self.assertEqual(episodes[0]["channel_description"], "A thoughtful channel description.")

    def test_long_episode_descriptions_truncate_at_word_boundaries(self):
        item = ET.fromstring(f"<item><description>{'word ' * 79}bestseller</description></item>")

        description = episode_description(item)

        self.assertEqual(description, ("word " * 79).strip() + "…")

    def test_atom_relative_links_and_iso_dates(self):
        feed = b"""<?xml version='1.0'?>
        <feed xmlns='http://www.w3.org/2005/Atom'>
          <entry><title>Atom episode</title><link href='/episodes/42'/>
            <link rel='enclosure' type='image/png' href='/cover.png'/>
            <duration>PT1H2M5S</duration>
            <published>2026-10-12T12:30:00Z</published></entry>
        </feed>"""

        episodes = parse_feed(feed, "Atom Show", FEED_URL, NOW)

        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["url"], "https://example.test/episodes/42")
        self.assertEqual(episodes[0]["episode"], "Atom episode")
        self.assertEqual(episodes[0]["episode_artwork_url"], "https://example.test/cover.png")
        self.assertEqual(episodes[0]["duration"], "1 hr 2 min")

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

    def test_only_latest_three_episode_images_per_feed_are_selected(self):
        episodes = [
            {
                "show": "Example Show",
                "feed_url": FEED_URL,
                "published_at": f"2026-10-{day:02d}T12:00:00+00:00",
                "episode_artwork_url": f"https://example.test/cover-{day}.png",
            }
            for day in range(1, 6)
        ]

        sources = latest_episode_artwork_sources(episodes)

        self.assertEqual(
            set(sources),
            {f"https://example.test/cover-{day}.png" for day in (3, 4, 5)},
        )

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

    def test_cached_artwork_preserves_transparency_for_light_poster_themes(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "artwork.png"
            source = Image.new("RGBA", (512, 512), (30, 90, 120, 255))
            source.putpixel((0, 0), (30, 90, 120, 0))
            image_buffer = BytesIO()
            source.save(image_buffer, format="PNG")

            with patch("fetch_episodes.urlopen", return_value=BytesIO(image_buffer.getvalue())):
                saved_path, status = cache_artwork_image("https://example.test/art.png", cache_path)

            assert saved_path is not None
            with Image.open(saved_path) as cached:
                alpha_extrema = cached.getchannel("A").getextrema()

        self.assertEqual(status, "downloaded")
        self.assertEqual(alpha_extrema, (0, 255))

    def test_cached_channel_artwork_is_reused_without_network_access(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            cached_path = cache_dir / f"{hashlib.sha256(FEED_URL.encode()).hexdigest()}-v2.png"
            cached_path.write_bytes(b"cached artwork")

            with patch("fetch_episodes.urlopen") as urlopen_mock:
                path, status = cache_feed_artwork(FEED_URL, None, cache_dir)

        self.assertEqual(path, cached_path)
        self.assertEqual(status, "cached")
        urlopen_mock.assert_not_called()

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
            "description": "A useful summary.",
            "previously_posted": {"edition": "OCTOBER 2026", "generated_at": "2026-10-01"},
        }

        page = render_page([episode], 1, 0, 0, "October 13, 2026")

        self.assertNotIn("</script><script>alert(1)", page)
        self.assertIn("\\u003c/script>", page)
        self.assertIn("Earlier poster", page)
        self.assertIn("1 previously posted", page)
        self.assertIn('data-page-version="17"', page)
        self.assertIn("up to 400 characters", page)
        self.assertIn("Episode tags (edit these suggestions for this episode only)", page)
        self.assertIn("Common channel tags (suggestions preloaded for episode tags)", page)
        self.assertIn("Channel description / editorial note (up to 400 characters)", page)
        self.assertIn("function applyChannelMetadata(metadata)", page)
        self.assertIn("if(tags.length || reviewedTagOverrides.has(index) || reviewedChannelTagOverrides.has(episode.feed_url)) slot.tags = tags;", page)
        self.assertIn("reviewedChannelDescriptionOverrides.add(feedUrl)", page)
        self.assertIn("reviewedChannelTagOverrides.add(feedUrl)", page)
        self.assertIn("Edit selection", page)
        self.assertIn("Suggest summary + tags", page)
        self.assertIn("LLM suggestions unavailable:", page)
        self.assertIn("details.open = false", page)
        self.assertIn("See Settings → Recent LLM diagnostics", page)
        self.assertIn("/api/llm/suggest", page)
        self.assertIn("Process newest", page)
        self.assertNotIn("Process new/updated suggestions", page)
        self.assertIn('id="bulkSuggestionBatchSize" type="number" min="1" step="1" value="10"', page)
        self.assertNotIn('id="bulkSuggestionBatchSize" type="number" min="1" max=', page)
        self.assertIn("const maximum = pending", page)
        self.assertNotIn("MAX_BULK_SUGGESTION_BATCH_SIZE", page)
        self.assertIn("pending.slice(0, batchSize)", page)
        self.assertIn("Choose how many of the newest eligible episodes to process per batch.", page)
        self.assertIn("bulkSuggestionBatchSize.addEventListener(\"input\", updateBulkSuggestionControls)", page)
        self.assertIn("Another batch will not start automatically.", page)
        self.assertIn("Stop after current", page)
        self.assertIn("suggestionIsCurrent", page)
        self.assertIn("AI processed · v", page)
        self.assertIn('draftDetails.className = "llm-draft-preview"', page)
        self.assertIn("draftHeading.textContent = `AI draft: ${draftSnippet", page)
        self.assertIn("draftSummary.textContent = draftSummaryText", page)
        self.assertIn("draftTags.textContent = savedTags.length", page)
        self.assertIn("/api/llm/suggestions", page)
        self.assertIn("description.textContent = episode.description", page)
        self.assertIn("slot.summary = summary", page)
        self.assertIn("candidate-selection", page)
        self.assertIn("poster-history", page)
        self.assertIn("function applyPosterHistory(records)", page)
        self.assertIn("reportSelection();", page)


if __name__ == "__main__":
    unittest.main()

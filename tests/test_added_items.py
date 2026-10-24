import json
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import added_feeds
import feed_discovery
import link_preview
import server

NOW = datetime(2026, 10, 24, 9, 30, tzinfo=timezone.utc)
VIDEO = "https://www.youtube.com/watch?v=abcdefghijk"
ARTICLE = "https://blog.example/2026/10/post"


class AddedFeedStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_each_media_type_is_its_own_valid_rss_feed(self):
        self.assertEqual(added_feeds.add(self.root, [VIDEO, VIDEO], "video", NOW), [VIDEO])
        self.assertEqual(added_feeds.add(self.root, [ARTICLE, VIDEO], "article", NOW), [ARTICLE])

        rss = ET.parse(self.root / "added-videos.xml").getroot()
        self.assertEqual(rss.tag, "rss")
        self.assertEqual(rss.find("channel/title").text, "Added videos")
        item = rss.find("channel/item")
        self.assertEqual(item.find("link").text, VIDEO)
        self.assertIsNotNone(item.find("pubDate").text)
        # An undated item carries the day it was added, marked as not a release date.
        self.assertEqual(item.find(f"{{{added_feeds.PPS}}}dateKnown").text, "false")
        self.assertEqual([entry["url"] for entry in added_feeds.read_items(self.root, "article")], [ARTICLE])

    def test_details_round_trip_through_standard_rss_fields(self):
        added_feeds.add(self.root, [VIDEO], "video", NOW)
        added_feeds.update(self.root, VIDEO, {
            "episode": "Trains are great",
            "show": "Not Just Bikes",
            "feed_url": "https://www.youtube.com/@NotJustBikes",
            "description": "Why trains are great.",
            "published_at": "2026-01-02T03:04:05+00:00",
            "duration_seconds": 750,
            "image_url": "https://i.ytimg.com/vi/abcdefghijk/maxresdefault.jpg",
            "artwork_path": "user-data/cache/artwork/link-x-v2.png",
            "tags": ["Trains", "Urbanism"],
            "status": "ready",
        })

        item = added_feeds.read_items(self.root, "video")[0]
        self.assertEqual(item["episode"], "Trains are great")
        self.assertEqual(item["show"], "Not Just Bikes")
        self.assertEqual(item["date"], "January 2, 2026")
        self.assertEqual(item["duration"], "12 min")
        self.assertEqual(item["summary"], "Why trains are great.")
        self.assertEqual(item["tags"], ["Trains", "Urbanism"])
        self.assertEqual(item["status"], "ready")
        self.assertEqual(item["added_at"], NOW.isoformat())
        rss = ET.parse(self.root / "added-videos.xml").getroot()
        self.assertEqual(rss.find(f"channel/item/{{{added_feeds.ITUNES}}}duration").text, "750")
        self.assertIsNone(rss.find(f"channel/item/{{{added_feeds.PPS}}}dateKnown"))

    def test_moving_an_item_changes_its_media_type(self):
        added_feeds.add(self.root, [ARTICLE], "article", NOW)
        moved = added_feeds.move(self.root, ARTICLE, "podcast")

        self.assertEqual(moved["media"], "podcast")
        self.assertEqual(added_feeds.read_items(self.root, "article"), [])
        self.assertEqual(added_feeds.read_items(self.root, "podcast")[0]["added_at"], NOW.isoformat())
        with self.assertRaises(ValueError):
            added_feeds.remove(self.root, "https://missing.example/")


class InspectLinkTests(unittest.TestCase):
    def inspect(self, url, responses):
        def fetch(target, limit, accept="*/*"):
            for prefix, body in responses.items():
                if target.startswith(prefix):
                    data = json.dumps(body).encode() if isinstance(body, dict) else body
                    return data, "utf-8", target
            raise URLError(f"unexpected fetch {target}")

        with patch.object(feed_discovery, "fetch_bytes", side_effect=fetch), patch.object(link_preview, "fetch_bytes", side_effect=fetch):
            return feed_discovery.inspect_link(url)

    def test_youtube_video_is_one_item_with_its_channel_offered(self):
        result = self.inspect(VIDEO, {"https://www.youtube.com/oembed?": {
            "title": "Trains are great", "author_name": "Not Just Bikes", "author_url": "https://www.youtube.com/@NotJustBikes",
        }})
        self.assertEqual(result["default"], "item")
        self.assertEqual(result["item"], {"media": "video", "title": "Trains are great"})
        self.assertEqual(result["follow"]["url"], "https://www.youtube.com/@NotJustBikes")

    def test_blog_home_page_means_follow_and_a_post_means_one_article(self):
        page = b"""<html><head><title>A Blog</title>
        <link rel="alternate" type="application/atom+xml" href="/feed.xml"></head></html>"""
        feed = b"""<feed xmlns="http://www.w3.org/2005/Atom"><title>A Blog</title><entry><title>Post</title></entry></feed>"""
        home = self.inspect("https://blog.example/", {"https://blog.example/feed.xml": feed, "https://blog.example/": page})
        post = self.inspect(ARTICLE, {"https://blog.example/feed.xml": feed, ARTICLE: page})

        self.assertEqual(home["default"], "follow")
        self.assertEqual(home["follow"]["media"], "article")
        self.assertEqual(post["default"], "item")
        self.assertEqual(post["item"]["media"], "article")
        self.assertEqual(post["follow"]["feed_url"], "https://blog.example/feed.xml")

    def test_media_guess_for_single_items(self):
        self.assertEqual(feed_discovery.guess_item_media("https://vimeo.com/123"), "video")
        self.assertEqual(feed_discovery.guess_item_media("https://open.spotify.com/episode/1"), "podcast")
        self.assertEqual(feed_discovery.guess_item_media("https://news.example/a", {"og:type": "video.other"}), "video")
        self.assertEqual(feed_discovery.guess_item_media("https://news.example/a", {"og:type": "article"}), "article")

    def test_spotify_shows_cannot_be_followed(self):
        result = self.inspect("https://open.spotify.com/show/abc", {})
        self.assertIsNone(result["follow"])
        self.assertIn("Spotify", result["error"])


class AddFlowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.config_path = self.root / "user-data" / "config.json"
        self.config_path.parent.mkdir()
        self.config_path.write_text(json.dumps({"opml_path": "user-data/subscriptions.opml", "poster_layout": "list", "slots": []}), encoding="utf-8")
        artwork = self.root / "user-data" / "cache" / "artwork" / "link-abc-v2.png"
        artwork.parent.mkdir(parents=True)
        artwork.write_bytes(b"png")
        self.artwork = artwork
        self.patches = [
            patch.object(server, "CONFIG_PATH", self.config_path),
            patch.object(server, "USER_DATA_DIR", self.root / "user-data"),
            patch.object(server, "BASE_DIR", self.root),
        ]
        for active in self.patches:
            active.start()

    def tearDown(self):
        for active in reversed(self.patches):
            active.stop()
        self.directory.cleanup()

    def test_add_files_items_by_media_and_follows_feeds_without_touching_config(self):
        result = server.add_from_links([
            {"url": VIDEO, "item": True, "media": "video", "follow": {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC1", "title": "Not Just Bikes"}},
            {"url": ARTICLE, "item": True, "media": "article"},
        ])

        self.assertEqual(result["added"], [VIDEO, ARTICLE])
        self.assertEqual(result["followed"], 1)
        self.assertEqual({item["url"]: item["media"] for item in server.get_added()}, {VIDEO: "video", ARTICLE: "article"})
        opml = (self.root / "user-data" / "subscriptions.opml").read_bytes()
        self.assertEqual([feed["title"] for feed in server.list_opml_subscriptions(opml)], ["Not Just Bikes"])
        self.assertNotIn("links", json.loads(self.config_path.read_text()))
        self.assertEqual([summary["count"] for summary in server.added_feed_summaries()], [0, 1, 1])

    def test_item_can_be_shortlisted_and_picked_before_its_details_arrive(self):
        server.add_from_links([{"url": VIDEO, "item": True, "media": "video"}])
        bare = server.get_added()[0]
        copy = {key: bare[key] for key in ("show", "episode", "date", "url", "feed_url", "media")}
        server.add_to_shortlist(copy)
        server.add_to_draft({**copy, "type": "fixed"})
        server.update_draft_slot(VIDEO, {"summary": "My own words."})
        resolved = {
            **link_preview.bare_link(VIDEO, NOW), "status": "ready", "show": "Not Just Bikes", "episode": "Trains are great",
            "feed_url": "https://www.youtube.com/@NotJustBikes", "description": "Why trains are great.",
            "published_at": "2026-01-02T11:04:05+00:00", "artwork_path": self.artwork,
        }

        with patch.object(link_preview, "resolve_link", return_value=(resolved, [])):
            result = server.fetch_added_details(VIDEO)

        self.assertTrue(result["shortlist_changed"] and result["draft_changed"])
        self.assertEqual(result["item"]["artwork_path"], "user-data/cache/artwork/link-abc-v2.png")
        self.assertEqual(result["item"]["added_at"], bare["added_at"])
        self.assertEqual(server.get_shortlist()[0]["episode"], "Trains are great")
        slot = server.get_draft_slots(server.load_config())[0]
        self.assertEqual((slot["show"], slot["date"], slot["media"]), ("Not Just Bikes", "January 2, 2026", "video"))
        self.assertEqual(slot["summary"], "My own words.")
        server.validate_slots([slot])

    def test_failed_fetch_keeps_the_item_and_its_error(self):
        server.add_from_links([{"url": ARTICLE, "item": True, "media": "article"}])
        failed = {**link_preview.bare_link(ARTICLE, NOW), "status": "failed", "error": "page: offline"}

        with patch.object(link_preview, "resolve_link", return_value=(failed, ["page: offline"])):
            result = server.fetch_added_details(ARTICLE)

        self.assertEqual((result["item"]["status"], result["item"]["error"]), ("failed", "page: offline"))
        self.assertEqual(result["item"]["episode"], ARTICLE)

    def test_changing_type_moves_the_item_and_updates_saved_copies(self):
        server.add_from_links([{"url": ARTICLE, "item": True, "media": "article"}])
        bare = server.get_added()[0]
        server.add_to_shortlist({key: bare[key] for key in ("show", "episode", "date", "url", "feed_url", "media")})

        result = server.move_added(ARTICLE, "podcast")

        self.assertEqual(result["item"]["media"], "podcast")
        self.assertTrue(result["shortlist_changed"])
        self.assertEqual(server.get_shortlist()[0]["media"], "podcast")
        with self.assertRaises(ValueError):
            server.move_added(ARTICLE, "radio")

    def test_links_saved_in_config_by_earlier_builds_move_into_the_feeds(self):
        config = json.loads(self.config_path.read_text())
        config["links"] = [
            {"url": VIDEO, "show": "Not Just Bikes", "episode": "Trains", "status": "ready", "added_at": NOW.isoformat()},
            {"url": ARTICLE, "status": "pending"},
        ]
        self.config_path.write_text(json.dumps(config), encoding="utf-8")

        items = {item["url"]: item for item in server.get_added()}

        self.assertEqual((items[VIDEO]["media"], items[VIDEO]["episode"]), ("video", "Trains"))
        self.assertEqual(items[ARTICLE]["media"], "article")
        self.assertNotIn("links", json.loads(self.config_path.read_text()))

    def test_details_typed_when_adding_are_kept_over_fetched_ones(self):
        server.add_from_links([{"url": VIDEO, "item": True, "media": "video", "details": {
            "title": "My title", "summary": "Why it matters.", "tags": ["#Transit", "transit", "Cities"],
        }}])
        item = server.get_added()[0]
        self.assertEqual((item["episode"], item["summary"], item["tags"]), ("My title", "Why it matters.", ["Transit", "Cities"]))
        resolved = {**link_preview.bare_link(VIDEO, NOW), "status": "ready", "episode": "Page title",
                    "description": "Page description.", "tags": ["Page"], "show": "Channel"}

        with patch.object(link_preview, "resolve_link", return_value=(resolved, [])):
            fetched = server.fetch_added_details(VIDEO)["item"]

        self.assertEqual((fetched["episode"], fetched["summary"], fetched["tags"]), ("My title", "Why it matters.", ["Transit", "Cities"]))
        self.assertEqual((fetched["show"], fetched["description"]), ("Channel", "Page description."))

    def test_a_note_and_tags_typed_for_a_followed_feed_become_its_channel_notes(self):
        feed = "https://www.youtube.com/feeds/videos.xml?channel_id=UC1"
        server.add_from_links([{"url": VIDEO, "item": False, "follow": {
            "url": feed, "title": "Not Just Bikes", "note": "Urbanism explainers.", "tags": ["Cities"],
        }}])
        notes = server.load_config()["subscription_metadata"][feed]
        self.assertEqual(notes, {"channel_description": "Urbanism explainers.", "tags": ["Cities"]})

    def test_an_invalid_detail_adds_nothing(self):
        with self.assertRaises(ValueError):
            server.add_from_links([
                {"url": ARTICLE, "item": True, "media": "article"},
                {"url": VIDEO, "item": True, "media": "video", "details": {"summary": "x" * 401}},
            ])
        self.assertEqual(server.get_added(), [])

    def test_a_poster_may_mix_media_types(self):
        slots = [
            {"type": "fixed", "show": "Show", "episode": "One", "date": "October 1, 2026", "url": "https://example.test/one", "feed_url": "https://example.test/feed.xml"},
            {"type": "fixed", "show": "Channel", "episode": "Two", "date": "October 2, 2026", "url": VIDEO, "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC1"},
        ]
        cleaned = server.validate_slots(slots)
        self.assertEqual([slot["media"] for slot in cleaned], ["podcast", "video"])
        self.assertEqual(server.poster_media(cleaned), "mixed")
        self.assertEqual(server.poster_media(cleaned[:1]), "podcast")


class PosterMediaWordingTests(unittest.TestCase):
    def generate(self, media_types):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = json.loads((Path(server.BASE_DIR) / "config.example.json").read_text(encoding="utf-8"))
            config.update({
                "output_pdf": str(root / "poster.pdf"),
                "feed_cache_dir": str(root / "cache"),
                "poster_history_dir": str(root / "history"),
                "slots": [
                    {"type": "fixed", "show": f"Show {index}", "episode": f"Item {index}", "date": "October 1, 2026",
                     "url": f"https://example.invalid/{index}", "feed_url": f"https://example.invalid/feed-{index}.xml", "media": media}
                    for index, media in enumerate(media_types)
                ],
            })
            config_path = root / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(Path(server.BASE_DIR) / "gen.py")],
                env={**os.environ, "PODCAST_POSTER_CONFIG": str(config_path)},
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            manifest = next((root / "history").glob("poster-*.json"))
            return json.loads(manifest.read_text(encoding="utf-8"))

    def test_heading_follows_the_media_type_and_mixed_posters_are_neutral(self):
        mixed = self.generate(["podcast", "video", "article"])
        videos = self.generate(["video", "video"])

        self.assertEqual((mixed["media"], mixed["title"]), ("mixed", "WORTH YOUR TIME THIS MONTH"))
        self.assertEqual((videos["media"], videos["title"]), ("video", "VIDEOS WORTH WATCHING THIS MONTH"))
        self.assertEqual([slot["media"] for slot in mixed["slots"]], ["podcast", "video", "article"])


if __name__ == "__main__":
    unittest.main()

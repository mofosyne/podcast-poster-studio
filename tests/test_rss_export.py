import json
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

import rss_export
import server

ENTRY = {
    "show": "Not Just Bikes",
    "episode": "Trains are great",
    "date": "October 12, 2026",
    "url": "https://www.youtube.com/watch?v=abcdefghijk",
    "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC1",
    "summary": "Why trains are great.",
    "tags": ["Transit"],
}


class RssExportTests(unittest.TestCase):
    def test_shortlist_feed_lists_each_item_with_its_type(self):
        rss = ET.fromstring(rss_export.shortlist_rss([ENTRY, {"url": "https://example.test/a", "date": "Added October 1, 2026"}], "http://127.0.0.1:8765"))
        items = rss.findall("channel/item")

        self.assertEqual([item.find("title").text for item in items], ["Trains are great", "https://example.test/a"])
        self.assertEqual(items[0].find("description").text, "Why trains are great.")
        self.assertEqual(items[0].find("pubDate").text, "Mon, 12 Oct 2026 00:00:00 GMT")
        self.assertEqual(items[0].find(f"{{{rss_export.PPS}}}media").text, "video")
        self.assertEqual(items[1].find("pubDate").text, "Thu, 01 Oct 2026 00:00:00 GMT")

    def test_posters_feed_has_one_item_per_poster_with_its_pdf(self):
        record = {"manifest": "poster-20261024-101500.json", "title": "WORTH YOUR TIME THIS MONTH", "edition": "OCTOBER 2026",
                  "generated_at": "2026-10-24T10:15:00+11:00", "pdf": "poster-20261024-101500.pdf", "slots": [ENTRY]}
        rss = ET.fromstring(rss_export.posters_rss([record], "http://127.0.0.1:8765", lambda record: 2048))
        item = rss.find("channel/item")

        self.assertEqual(item.find("title").text, "WORTH YOUR TIME THIS MONTH · OCTOBER 2026")
        self.assertEqual(item.find("pubDate").text, "Fri, 23 Oct 2026 23:15:00 GMT")
        enclosure = item.find("enclosure")
        self.assertEqual(enclosure.get("url"), "http://127.0.0.1:8765/api/history/poster-20261024-101500.json/download")
        self.assertEqual((enclosure.get("type"), enclosure.get("length")), ("application/pdf", "2048"))
        self.assertIn("Trains are great", item.find("description").text)

    def test_feeds_are_served_over_http(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            history = root / "history"
            history.mkdir()
            (history / "poster-20261024-101500.json").write_text(json.dumps({
                "generated_at": "2026-10-24T10:15:00+00:00", "title": "Posters", "pdf": "poster-20261024-101500.pdf", "slots": [ENTRY],
            }), encoding="utf-8")
            (history / "poster-20261024-101500.pdf").write_bytes(b"%PDF-1.4 test")
            config_path = root / "config.json"
            config_path.write_text(json.dumps({"poster_history_dir": str(history), "shortlist": [ENTRY]}), encoding="utf-8")
            with patch.object(server, "CONFIG_PATH", config_path):
                httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.LocalHandler)
                thread = threading.Thread(target=httpd.serve_forever, daemon=True)
                thread.start()
                try:
                    base_url = f"http://127.0.0.1:{httpd.server_port}"
                    with urlopen(base_url + "/feeds/shortlist.xml") as response:
                        shortlist = ET.fromstring(response.read())
                        content_type = response.headers.get("Content-Type")
                    with urlopen(base_url + "/feeds/posters.xml") as response:
                        posters = ET.fromstring(response.read())
                finally:
                    httpd.shutdown()
                    httpd.server_close()
                    thread.join(timeout=2)

        self.assertTrue(content_type.startswith("application/rss+xml"))
        self.assertEqual(shortlist.find("channel/item/link").text, ENTRY["url"])
        enclosure = posters.find("channel/item/enclosure")
        self.assertTrue(enclosure.get("url").startswith(f"http://127.0.0.1:"))
        self.assertEqual(enclosure.get("length"), str(len(b"%PDF-1.4 test")))


if __name__ == "__main__":
    unittest.main()

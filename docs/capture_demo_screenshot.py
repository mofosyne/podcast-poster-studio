import json
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import server
from fetch_episodes import render_page

OUTPUT = ROOT / "docs" / "interface.png"
FEEDS = [
    ("Example: Climate Briefing", "climate", "Clear reporting on climate policy, clean energy, and local action.", ["Climate", "Environment"], ("#244f46", "#83c56a")),
    ("Example: Field Notes", "field", "Ecologists explore biodiversity and the changing world around us.", ["Ecology", "Biodiversity"], ("#795834", "#e4bd72")),
    ("Example: Civic Signals", "civic", "Conversations about Australian politics, public policy, and democracy.", ["Australian Politics", "Democracy"], ("#3a496e", "#91b7e2")),
    ("Example: The Long View", "history", "Historians connect the past with questions shaping life today.", ["History", "Culture"], ("#68404d", "#dc9f8d")),
]


def draw_cover(path, label, colors):
    image = Image.new("RGB", (320, 320), colors[0])
    draw = ImageDraw.Draw(image)
    draw.ellipse((174, -25, 370, 171), fill=colors[1])
    draw.ellipse((-85, 195, 126, 406), fill=colors[1])
    draw.rounded_rectangle((35, 54, 285, 266), radius=22, outline="#ffffff", width=5)
    draw.text((55, 145), label.upper(), fill="#ffffff", stroke_width=1)
    image.save(path, format="PNG")


def main():
    browser = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    if not browser:
        raise RuntimeError("Install Chromium or Google Chrome to regenerate the screenshot.")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        user_data = root / "user-data"
        artwork_dir = user_data / "cache" / "artwork"
        artwork_dir.mkdir(parents=True)
        outlines = []
        episodes = []
        saved_metadata = {}

        for index, (title, slug, description, tags, colors) in enumerate(FEEDS, start=1):
            url = f"https://example.test/{slug}.xml"
            filename = f"demo-{index}.png"
            draw_cover(artwork_dir / filename, slug, colors)
            outlines.append(f'<outline text="{escape(title)}" xmlUrl="{url}"/>')
            episodes.append({
                "show": title,
                "episode": f"A recent conversation from {slug}",
                "date": "October 18, 2026",
                "published_at": f"2026-10-{18-index:02d}T10:00:00+00:00",
                "url": f"https://example.test/episode-{index}",
                "feed_url": url,
                "description": description,
                "feed_description": description,
                "channel_artwork_path": f"user-data/cache/artwork/{filename}",
                "artwork_path": f"user-data/cache/artwork/{filename}",
                "tags": tags,
            })
            if index <= 2:
                saved_metadata[url] = {"channel_description": description, "tags": tags}

        opml_path = user_data / "subscriptions.opml"
        opml_path.write_text(
            "<?xml version='1.0'?><opml version='2.0'><body>" + "".join(outlines) + "</body></opml>",
            encoding="utf-8",
        )
        candidate_path = user_data / "episode-candidates.html"
        candidate_path.write_text(render_page(episodes, len(FEEDS), len(FEEDS), 0, "Demo data"), encoding="utf-8")
        config_path = user_data / "config.json"
        config_path.write_text(json.dumps({
            "opml_path": str(opml_path),
            "episode_candidates_html": str(candidate_path),
            "poster_history_dir": str(user_data / "history" / "posters"),
            "output_pdf": str(user_data / "poster.pdf"),
            "poster_title": "EPISODES WORTH LISTENING TO THIS {period}",
            "poster_period": "month",
            "poster_layout": "list",
            "poster_theme": "dark",
            "subscription_metadata": saved_metadata,
            "slots": [],
            "llm": {"enabled": False},
        }), encoding="utf-8")

        with (
            patch.object(server, "BASE_DIR", root),
            patch.object(server, "USER_DATA_DIR", user_data),
            patch.object(server, "CONFIG_PATH", config_path),
            patch.object(server, "LLM_SUGGESTIONS_PATH", user_data / "llm-suggestions.json"),
        ):
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.LocalHandler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                result = subprocess.run([
                    browser,
                    "--headless=new",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--hide-scrollbars",
                    "--window-size=1440,1500",
                    "--virtual-time-budget=4000",
                    f"--screenshot={OUTPUT}",
                    f"http://127.0.0.1:{httpd.server_port}/",
                ], capture_output=True, text=True, timeout=45)
                if result.returncode:
                    raise RuntimeError(result.stderr[-3000:] or "Browser screenshot capture failed.")
            finally:
                httpd.shutdown()
                httpd.server_close()
                thread.join(timeout=3)

    if not OUTPUT.is_file():
        raise RuntimeError("Browser did not create the screenshot.")
    print(OUTPUT)


if __name__ == "__main__":
    main()

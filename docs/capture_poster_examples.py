"""Render example posters with fictional demo episodes for the README.

Writes docs/posters/*.png. Needs the project dependencies and `pdftoppm`
(from poppler-utils) to rasterize the PDFs.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "docs" / "posters"
DPI = 60

SHOWS = [
    ("Example: Climate Briefing", ("#244f46", "#83c56a"), ["Climate", "Energy policy"]),
    ("Example: Field Notes", ("#795834", "#e4bd72"), ["Ecology", "Biodiversity"]),
    ("Example: Civic Signals", ("#3a496e", "#91b7e2"), ["Politics", "Democracy"]),
    ("Example: The Long View", ("#68404d", "#dc9f8d"), ["History", "Culture"]),
]
TITLES = [
    "Wetlands, birds and the farmers who changed their minds",
    "What a single hedgerow can tell us about a whole valley",
    "How a small council rewrote its budget with residents",
    "The forgotten engineers behind the city's first trams",
    "Why the sea wall debate keeps coming back",
    "Counting moths at midnight with volunteer scientists",
]
SUMMARY = (
    "The hosts dig into how a small coastal town rebuilt its wetlands after decades of drainage, what the "
    "returning birds tell scientists about water quality, and why local farmers ended up championing a project "
    "they once fought. They also unpack the funding model, the setbacks along the way, and what other regions "
    "could borrow from the approach."
)

EXAMPLES = [
    ("single", "single", "dark", 1),
    ("list-2", "list", "dark", 2),
    ("list-3", "list", "dark", 3),
    ("list-6", "list", "dark", 6),
    ("list-3-ink-saving", "list", "ink-saving", 3),
]


def draw_cover(path, colors):
    image = Image.new("RGB", (512, 512), colors[0])
    draw = ImageDraw.Draw(image)
    draw.ellipse((280, -40, 590, 270), fill=colors[1])
    draw.ellipse((-130, 310, 200, 640), fill=colors[1])
    image.save(path, format="PNG")


def main():
    if not shutil.which("pdftoppm"):
        raise RuntimeError("Install pdftoppm (poppler-utils) to rasterize the example posters.")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        artwork_dir = root / "cache" / "artwork"
        artwork_dir.mkdir(parents=True)
        for index, (_, colors, _) in enumerate(SHOWS):
            draw_cover(artwork_dir / f"demo-{index}.png", colors)

        def slot(index):
            show, _, tags = SHOWS[index % len(SHOWS)]
            return {
                "type": "fixed",
                "show": show,
                "episode": TITLES[index],
                "date": f"October {23 - index}, 2026",
                "duration": f"{38 + index * 7} min",
                "url": f"https://example.test/episode-{index + 1}",
                "feed_url": f"https://example.test/feed-{index % len(SHOWS)}.xml",
                "summary": SUMMARY,
                "tags": tags,
                "artwork_path": str(artwork_dir / f"demo-{index % len(SHOWS)}.png"),
            }

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for name, layout, theme, count in EXAMPLES:
            pdf_path = root / f"{name}.pdf"
            config_path = root / f"{name}.json"
            config_path.write_text(json.dumps({
                "feed_cache_dir": str(root / "cache"),
                "poster_history_dir": str(root / "history"),
                "output_pdf": str(pdf_path),
                "poster_title": "EPISODES WORTH LISTENING TO THIS {period}",
                "poster_period": "month",
                "poster_layout": layout,
                "poster_theme": theme,
                "slots": [slot(index) for index in range(count)],
            }), encoding="utf-8")
            subprocess.run(
                [sys.executable, str(ROOT / "gen.py"), "--preview"],
                cwd=ROOT,
                env={**os.environ, "PODCAST_POSTER_CONFIG": str(config_path)},
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["pdftoppm", "-png", "-r", str(DPI), "-singlefile", str(pdf_path), str(OUTPUT_DIR / name)],
                check=True,
            )
            print(OUTPUT_DIR / f"{name}.png")


if __name__ == "__main__":
    main()

# Podcast poster generator

A local tool for reviewing podcast feeds and generating a one-page PDF poster with episode QR codes.

## Requirements

- Python 3.10 or newer
- An AntennaPod OPML export to scan the full subscription list
- Optional: [`just`](https://just.systems) for command shortcuts

## Setup

Clone or download the repository, then run:

```sh
just setup
```

This creates a virtual environment, installs the Python dependencies, and copies `config.example.json` to `user-data/config.json` if you do not already have a local config. Without `just`, create the environment and config manually:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
mkdir -p user-data
cp config.example.json user-data/config.json
```

Copy your AntennaPod OPML export to `user-data/subscriptions.opml`. The example config already points there. Edit `user-data/config.json` to set poster slots and other preferences.

## Keep personal data local

Everything under `user-data/` is ignored by Git. It is intended for personal and generated files, including your OPML subscriptions, real config and selected slots, downloaded feed/artwork cache, candidate review page, generated PDFs, and poster history. The history is used to flag episodes that appeared on earlier posters.

Keep reusable code, tests, and `config.example.json` in the repository; do not add your personal config, subscriptions, cache, history, or generated posters to a shared repository. The example config contains no selected episodes. Poster generation needs at least one slot in your local config.

If you previously used the old `tools/episode-browser.html`, check its data for credential-bearing feed URLs and rotate any exposed credentials before sharing or publishing them.

## Commands

Run `just` to list recipes:

- `just setup` creates the local config if needed and installs dependencies.
- `just episodes` scans the full OPML feed history and builds the chronological review page. Extra script arguments can be forwarded, for example `just episodes -- --opml /path/to/feeds.opml`.
- `just resolve` resolves configured slot show names against the OPML and writes `user-data/resolved_feeds.json`.
- `just poster` generates the poster PDF and archives its snapshot.
- `just test` runs the unit test suite.
- `just check` checks Python syntax and local config JSON.

The commands can also be run with `.venv/bin/python` directly, for example `.venv/bin/python fetch_episodes.py`.

## Review all available episodes

Run:

```sh
just episodes
```

The script scans feeds in the OPML and creates `user-data/episode-candidates.html`, sorted newest-first across the full episode history each feed provides. Results are paged 200 at a time. Feed responses are cached under `user-data/cache/feeds/`; if a feed is temporarily unavailable, its cached response is used when possible. The page compares episodes with `user-data/history/posters/` and labels episodes that appeared on an earlier poster. You can still select one intentionally; the page warns before export. Filter by show or title, select up to eight episodes, and export slot entries to add to the `slots` array in `user-data/config.json`.

## Configure poster slots

`user-data/config.json` is the source of truth for poster content. Each slot is either fixed to a specific episode:

```json
{
  "type": "fixed",
  "show": "Example Podcast",
  "episode": "A selected older episode",
  "date": "October 12, 2024",
  "url": "https://example.com/episode",
  "feed_url": "https://example.com/feed.xml"
}
```

or dynamic, resolving to the newest dated episode in its feed each time the poster is generated:

```json
{
  "type": "latest",
  "show": "Example Podcast",
  "feed_url": "https://example.com/feed.xml"
}
```

The poster supports up to eight slots. Feed URLs are used for dynamic lookup and artwork; artwork is cached under `user-data/cache/artwork/`, with title-colored placeholder artwork used when no channel art is available.

## Generate and retain posters

Run:

```sh
just poster
```

The output path is configured by `output_pdf` (default: `user-data/podcast-poster.pdf`). Each successful generation also saves a timestamped PDF and a JSON snapshot of its resolved slots, title, and edition under `user-data/history/posters/`. The snapshots flag episodes already posted. Set `poster_period` to `month` or `week` to control the edition label.

# Podcast poster generator

A local tool for reviewing podcast feeds and generating a one-page PDF poster with episode QR codes.

![Podcast Poster Studio's Pick episodes step with fictional demo feeds](docs/interface.png)

The screenshot uses fictional demo subscriptions and artwork; it contains no personal feed data.

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

Everything under `user-data/` is ignored by Git. It is intended for personal and generated files, including your OPML subscriptions, real config and selected slots, downloaded feed/artwork cache, candidate review page, generated PDFs, poster history, and saved LLM drafts (`llm-suggestions.json`). The history is used to flag episodes that appeared on earlier posters; saved LLM drafts mark processed episodes and are versioned so newer suggestion rules can make old drafts eligible for reprocessing.

Keep reusable code, tests, and `config.example.json` in the repository; do not add your personal config, subscriptions, cache, history, or generated posters to a shared repository. The example config contains no selected episodes. Poster generation needs at least one slot in your local config.

If you previously used the old `tools/episode-browser.html`, check its data for credential-bearing feed URLs and rotate any exposed credentials before sharing or publishing them.

## Commands

Run `just` to list recipes:

- `just setup` creates the local config if needed and installs dependencies.
- `just episodes` scans the full OPML feed history and builds the chronological review page. Extra script arguments can be forwarded, for example `just episodes -- --opml /path/to/feeds.opml`.
- `just resolve` resolves configured slot show names against the OPML and writes `user-data/resolved_feeds.json`.
- `just poster` generates the poster PDF and archives its snapshot.
- `just web` starts the local browser-based workflow.
- `just test` runs the unit test suite.
- `just check` checks Python syntax and local config JSON.

The commands can also be run with `.venv/bin/python` directly, for example `.venv/bin/python fetch_episodes.py`.

## Use the integrated web workflow

Start the local server with:

```sh
just web
```

Open `http://127.0.0.1:8765/`. Making a poster takes three steps, shown across the top:

1. **Pick episodes** — tick up to six episodes (click anywhere on a row). Filter by show or title (press `/`), or switch between **All**, **★ Shortlisted**, and **✓ Selected**. Use **☆ Shortlist** to keep an episode for a later poster without adding it to this one. Episodes that appeared on an earlier poster are labelled, and you get a heads-up when you tick one.
2. **Edit text** — edit the summary and tags printed for each episode, and set the poster order with ↑ ↓. **Reset to feed text**, **Use channel tags**, and (with an LLM configured) **Suggest with AI** / **Use saved AI draft** each offer an Undo.
3. **Poster** — preview the poster and choose the layout (List, or Single episode when exactly one is picked) and theme. Previewing never touches history. **Generate & archive** saves the poster to History; the page then shows **Print PDF**, **Download PDF**, **Mark printed**, and **Start a new poster**. Generating the same poster twice is not possible: change the episodes, text, layout, or theme to make a new version.

Your picks and edits are the *poster draft*. It is saved on the server as you go (in `user-data/config.json` under `slots`), so reloading the page, rescanning feeds, or coming back later keeps it. Each step is its own address (`#pick`, `#edit`, `#poster`), so reloads and the browser's back button stay where you are. A tray at the bottom of Pick and Edit shows how many of the six places are filled and links to the next step. Shortlisted episodes are removed from the shortlist once they are archived on a poster. If a feed drops an episode you picked or shortlisted, it stays listed (marked as no longer in the latest scan) so you can still use or remove it.

**Subscriptions**, **History**, and **Settings** sit to the right of the steps:

- **Subscriptions** lists your feeds and imports or exports OPML. Import defaults to **Merge**, which keeps current feeds and adds new URLs without duplicates; choose **Replace** to swap the list (the app asks for confirmation). **Scan feeds** loads every episode the feeds provide; it is also available as **Rescan feeds** in Pick.
- **History** lists archived posters with **Print PDF**, **Download PDF**, **Preview PDF**, and **Regenerate PDF** (re-render with the current layout code). Mark each poster printed after printing or publishing it. Unprinted entries can be deleted normally; printed or older entries have an explicit **Force delete** action. **Clear poster archive** removes archived poster records and PDFs (printed and unprinted) while keeping subscriptions, episode data, caches, your poster draft, and the current poster PDF. Deleting history also removes its episode warnings.
- **Settings** configures the optional LLM connection described below.

The server binds only to loopback and is intended for local use. Stop it with Ctrl-C.

**Settings** shows whether common LLM environment variables are present. The app checks `LLM_BASE_URL`, `OPENAI_BASE_URL`, `OPENAI_API_BASE`, or `OLLAMA_HOST`, plus optional model (`LLM_MODEL`, `OPENAI_MODEL`, `OLLAMA_MODEL`) and key (`LLM_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_API_KEY`) variables. It only reports key-variable presence; secret values are never shown or saved. LLM connections are disabled by default, and startup does not probe ports or contact a model. If no endpoint is detected, Settings pre-fills `http://127.0.0.1:8080/v1` as an unverified suggestion; edit it if your service uses another address. Enable the connection to opt in; **Test connection** then requests only the service's model list. Choose a model ID from that list for suggestions. OpenAI-compatible and Ollama APIs are supported. The configured endpoint may be remote; only use a service you trust.

With an LLM configured, **Pick episodes** shows an **AI drafts** bar: set **Batch size** (default 10, up to the number of eligible episodes) to choose how many of the newest unprocessed or older-version episodes **Process newest X of Y** handles per run. Each run asks for confirmation, processes one episode at a time, saves drafts under `user-data/llm-suggestions.json`, and marks each completed episode; **Stop after current** ends the batch safely. Another batch starts only when you click again. Each processed row shows an inline AI summary snippet; expand it to read the full summary and tags. An episode picked after it was processed starts from its AI draft; in **Edit text**, **Use saved AI draft** applies a draft made later, and **Suggest with AI** regenerates one episode. Scans never make LLM requests. Bump `LLM_SUGGESTION_VERSION` in `server.py` when changing suggestion prompts or output rules; old-version drafts then become eligible for bulk reprocessing.

## Review all available episodes

Run:

```sh
just episodes
```

The scanner fetches feeds from the configured OPML and creates `user-data/episode-candidates.html`, sorted newest-first across the full episode history each feed provides. Results are paged 200 at a time. Feed responses are cached under `user-data/cache/feeds/`; if a feed is temporarily unavailable, its cached response is used when possible. Channel artwork is downloaded once per show, resized, and cached under `user-data/cache/artwork/`. Cached artwork preserves transparency for both poster themes; the first scan after the artwork-cache format update may download artwork again. For the three newest episodes of each show, the scanner also downloads episode-specific artwork when the feed provides it; that image is preferred, with channel art as the fallback. Older episodes reuse channel art. Images are cached by source, and the review page lazy-loads visible thumbnails. Feed descriptions appear in expandable, plain-text summaries capped at 400 characters. Episode durations are shown when feeds provide them. Missing or unavailable artwork gets a simple placeholder. The page compares episodes with `user-data/history/posters/` and labels episodes that appeared on an earlier poster. You can still select one intentionally; the page warns when you do. In the web app this page is the **Pick episodes** step. Opened directly as a standalone HTML file, it has its own **Review** step for summaries (up to 400 characters) and tags, and downloads the result as fixed slots that you can add to `user-data/config.json`.

## Subscription notes and tags

On **Subscriptions**, each feed shows cached channel artwork when available (falling back to episode artwork). Open **Edit channel note and tags** on a feed to write a local editorial note (up to 400 characters) and default tags, then **Save note and tags**. With an LLM configured, **Suggest with AI** fills that editor for review (nothing is saved until you click save), and the bulk **Fill in first X of Y with AI** control fills in channel notes and default tags for the selected number of incomplete subscriptions, processing feeds in OPML order because OPML has no subscription timestamps. Batch size defaults to 10 and is limited only by the remaining incomplete subscriptions. Each batch asks for confirmation; **Stop after current** lets you halt a long run after the active feed request finishes. This sends each feed's RSS description and up to three recent episode samples to your configured LLM and saves successful results while preserving any existing description or tags. For example, a channel note can say “Greens-affiliated podcast” and its default tag can be `Environment`. These annotations are stored in `user-data/config.json` under `subscription_metadata`, keyed by feed URL; they do not modify your OPML. Native channel descriptions from the RSS feed remain available as a fallback when no custom note is saved.

Episodes inherit their subscription's default tags in the episode list, and a picked episode starts with them (or with its AI draft's tags). In **Edit text**, change an episode's tags when its topic differs, or use **Use channel tags** to go back to the defaults; clearing the input removes the tags for that episode. Tags are comma-separated, deduplicated case-insensitively, and limited to 12 labels of 40 characters each. Poster tags print as hashtags; channel notes are review metadata and are not printed.

## Configure poster slots

`user-data/config.json` is the source of truth for poster content; the browser workflow edits its `slots` as your poster draft. Each slot is either fixed to a specific episode:

```json
{
  "type": "fixed",
  "show": "Example Podcast",
  "episode": "A selected older episode",
  "date": "October 12, 2024",
  "url": "https://example.com/episode",
  "feed_url": "https://example.com/feed.xml",
  "summary": "An optional short, edited blurb to print on the poster."
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

The list poster supports up to six slots. Set `poster_layout` to `"list"` or `"single"` in `user-data/config.json`; the single layout requires exactly one slot and uses `single_poster_title`. Set `poster_theme` to `"dark"` (default) or `"ink-saving"` for a white background. The browser workflow exposes both layout and theme selectors and saves them as you change them. Dynamic latest slots appear in the browser workflow's Edit step, where they can be reordered or removed but have no text to edit. Tags are rendered as stable-color, wrapping hashtag bubbles, with as many shown as fit the episode area. If a fixed slot includes a `summary`, it is printed as a short excerpt on the poster. A slot's `tags` override the subscription defaults; omit `tags` in manually configured slots to inherit defaults, or use an empty list to explicitly clear them. Dynamic latest slots also inherit subscription notes and tags. Feed URLs are used for dynamic lookup and artwork; artwork is cached under `user-data/cache/artwork/`, with title-colored placeholder artwork used when no episode or channel art is available.

## Generate and retain posters

Run:

```sh
just poster
```

The output path is configured by `output_pdf` (default: `user-data/podcast-poster.pdf`). Each successful generation also saves a timestamped PDF and a JSON snapshot of its resolved slots, title, and edition under `user-data/history/posters/`. The snapshots flag episodes already posted. Set `poster_period` to `month` or `week` to control the edition label.

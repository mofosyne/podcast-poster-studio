"""Fetch recent episodes from the OPML feeds and build a local review page."""

import argparse
import hashlib
import html
import json
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin, urlparse, urlunsplit
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "user-data" / "config.json"
MAX_FEED_BYTES = 12 * 1024 * 1024
USER_AGENT = "PodcastPoster/1.0 (local episode browser)"
MAX_WORKERS = 8

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Podcast Episode Archive</title>
<style>
:root{color-scheme:dark;--bg:#111412;--panel:#1a1f1c;--line:#303a34;--muted:#9ba79f;--text:#edf2ee;--accent:#4fd1c5;--orange:#f0ad63}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif;padding-bottom:92px}
main{max-width:980px;margin:36px auto;padding:0 22px}
h1{margin:0;font-size:clamp(25px,4vw,38px);letter-spacing:.02em}
.subtitle{color:var(--muted);margin:5px 0 22px}
.status{color:var(--muted);font-size:13px;margin-bottom:18px}
.controls{display:flex;gap:10px;margin-bottom:18px}
input[type=search]{flex:1;min-width:0;background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:7px;padding:11px 13px;font:inherit}
button{background:var(--accent);color:#10201d;border:0;border-radius:7px;padding:10px 15px;font-weight:700;cursor:pointer}
button:disabled{opacity:.4;cursor:default}
.episode{display:grid;grid-template-columns:26px minmax(0,1fr) auto;gap:12px;align-items:start;padding:15px 14px;border-top:1px solid var(--line)}
.episode:hover{background:#171c19}
.episode input{accent-color:var(--accent);width:17px;height:17px;margin:4px 0 0}
.show{font-weight:700;color:var(--accent)}
.title{font-size:16px;font-weight:600}
a{color:inherit;text-decoration:none}
a:hover{color:var(--accent);text-decoration:underline}
.meta{font-size:13px;color:var(--muted);margin-top:3px}
.date{font-size:13px;color:var(--orange);white-space:nowrap}
.posted-badge{display:inline-block;margin-left:8px;padding:1px 7px;border:1px solid #8b6841;border-radius:999px;color:var(--orange);font-size:11px;font-weight:600;vertical-align:1px}
.empty{color:var(--muted);padding:28px 14px;border-top:1px solid var(--line)}
.paging{display:flex;justify-content:center;align-items:center;gap:18px;margin:18px 0 34px;color:var(--muted);font-size:13px}
.paging button{background:var(--panel);color:var(--text);border:1px solid var(--line)}
.tray{position:fixed;bottom:0;left:0;right:0;background:#1a201d;border-top:1px solid var(--line);padding:12px 20px;box-shadow:0 -8px 24px #0005}
.tray-inner{max-width:980px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:15px}
#selection{color:var(--muted);font-size:13px}
.toast{position:fixed;bottom:78px;left:50%;transform:translateX(-50%);background:var(--orange);color:#21180e;padding:8px 15px;border-radius:6px;display:none}
.toast.show{display:block}
@media(max-width:600px){main{margin-top:24px;padding:0 14px}.episode{grid-template-columns:22px minmax(0,1fr)}.date{grid-column:2}.controls{flex-wrap:wrap}.tray-inner{align-items:flex-start;flex-direction:column}.tray button{width:100%}}
</style>
</head>
<body>
<main>
  <h1>Podcast episode archive</h1>
  <p class="subtitle">Browse the full episode history available from your subscriptions and choose up to eight for the poster.</p>
  <div class="status">__EPISODE_COUNT__ episodes from __FEED_COUNT__ feeds · __POSTED_COUNT__ previously posted · generated __GENERATED__ · __CACHE_STATUS__</div>
  <div class="controls"><input id="search" type="search" placeholder="Filter by show or episode title"><button id="clear">Clear selection</button></div>
  <div id="list"></div>
  <div class="paging"><button id="previousPage" type="button">Previous</button><span id="pageStatus"></span><button id="nextPage" type="button">Next</button></div>
</main>
<div class="tray"><div class="tray-inner"><div><strong id="selection">0 selected</strong><div class="meta">Export selections as fixed poster slots to add to user-data/config.json.</div></div><button id="export" disabled>Export selected episodes</button></div></div>
<div id="toast" class="toast"></div>
<script>
const EPISODES = __EPISODES__;
const list = document.getElementById("list");
const search = document.getElementById("search");
const pageStatus = document.getElementById("pageStatus");
const previousPage = document.getElementById("previousPage");
const nextPage = document.getElementById("nextPage");
const PAGE_SIZE = 200;
let currentPage = 0;
const selection = new Set();
const selectionLabel = document.getElementById("selection");
const exportButton = document.getElementById("export");
const toast = document.getElementById("toast");
let query = "";

function showToast(message){
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 1800);
}

function render(){
  const needle = query.trim().toLowerCase();
  const matches = EPISODES.map((episode, index) => ({episode, index})).filter(({episode}) =>
    !needle || `${episode.show} ${episode.episode}`.toLowerCase().includes(needle)
  );
  const pageCount = Math.max(1, Math.ceil(matches.length / PAGE_SIZE));
  currentPage = Math.min(currentPage, pageCount - 1);
  const firstIndex = currentPage * PAGE_SIZE;
  const visibleMatches = matches.slice(firstIndex, firstIndex + PAGE_SIZE);
  list.replaceChildren();
  if(!matches.length){
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No episodes match that filter.";
    list.append(empty);
  }
  for(const {episode, index} of visibleMatches){
    const row = document.createElement("div");
    row.className = "episode";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = selection.has(index);
    checkbox.setAttribute("aria-label", `Select ${episode.episode} from ${episode.show}`);
    checkbox.addEventListener("change", () => {
      if(checkbox.checked && selection.size >= 8){
        checkbox.checked = false;
        showToast("Select up to eight episodes for one poster.");
        return;
      }
      if(checkbox.checked){
        selection.add(index);
        if(episode.previously_posted){
          showToast(`Already appeared in ${episode.previously_posted.edition}.`);
        }
      } else selection.delete(index);
      updateSelection();
    });
    const body = document.createElement("div");
    const show = document.createElement("div");
    show.className = "show";
    show.textContent = episode.show;
    if(episode.previously_posted){
      const badge = document.createElement("span");
      badge.className = "posted-badge";
      badge.textContent = `Previously posted · ${episode.previously_posted.edition}`;
      show.append(badge);
    }
    const title = document.createElement("div");
    title.className = "title";
    const link = document.createElement("a");
    link.href = episode.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = episode.episode;
    title.append(link);
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = episode.date;
    body.append(show, title, meta);
    const date = document.createElement("div");
    date.className = "date";
    date.textContent = new Date(episode.published_at).toLocaleDateString(undefined, {year:"numeric", month:"short", day:"numeric"});
    row.append(checkbox, body, date);
    list.append(row);
  }
  previousPage.disabled = currentPage === 0;
  nextPage.disabled = currentPage >= pageCount - 1;
  pageStatus.textContent = matches.length
    ? `Showing ${firstIndex + 1}-${Math.min(firstIndex + PAGE_SIZE, matches.length)} of ${matches.length}`
    : "0 episodes";
  updateSelection();
}

function updateSelection(){
  selectionLabel.textContent = `${selection.size} selected`;
  exportButton.disabled = selection.size === 0;
}

search.addEventListener("input", event => { query = event.target.value; currentPage = 0; render(); });
previousPage.addEventListener("click", () => { currentPage -= 1; render(); });
nextPage.addEventListener("click", () => { currentPage += 1; render(); });
document.getElementById("clear").addEventListener("click", () => { selection.clear(); render(); });
exportButton.addEventListener("click", () => {
  const chosen = [...selection].map(index => {
    const {show, episode, date, url, feed_url} = EPISODES[index];
    return {type:"fixed", show, episode, date, url, feed_url};
  });
  const blob = new Blob([JSON.stringify(chosen, null, 2)], {type:"application/json"});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "selected-slots.json";
  link.click();
  URL.revokeObjectURL(link.href);
  showToast("Selected episodes exported.");
});
render();
</script>
</body>
</html>
"""


def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


def http_url(value, base_url=""):
    if not value:
        return None
    resolved = urljoin(base_url, value.strip())
    if urlparse(resolved).scheme.lower() not in {"http", "https"}:
        return None
    return resolved


def parse_date(value):
    if not value:
        return None
    value = value.strip()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def episode_date(item):
    for child in item:
        if local_name(child.tag) in {"pubdate", "published", "updated", "date"}:
            parsed = parse_date(child.text or "")
            if parsed:
                return parsed
    return None


def episode_link(item, feed_url):
    for child in item:
        if local_name(child.tag) != "link":
            continue
        href = child.get("href")
        rel = child.get("rel", "alternate").lower()
        if href and rel in {"alternate", ""}:
            return http_url(href, feed_url)
        if child.text and child.text.strip():
            return http_url(child.text, feed_url)
    for child in item:
        if local_name(child.tag) == "guid" and child.get("ispermalink", "true").lower() != "false":
            return http_url(child.text, feed_url)
    return None


def parse_feed(feed_data, show, feed_url, now):
    root = ET.fromstring(feed_data)
    episodes = []
    for node in root.iter():
        if local_name(node.tag) not in {"item", "entry"}:
            continue
        title = next(
            ((child.text or "").strip() for child in node if local_name(child.tag) == "title"),
            "",
        )
        published_at = episode_date(node)
        url = episode_link(node, feed_url)
        if not title or not published_at or not url or published_at > now:
            continue
        episodes.append({
            "show": show,
            "episode": title,
            "date": f"{published_at.strftime('%B')} {published_at.day}, {published_at.year}",
            "published_at": published_at.isoformat(),
            "url": url,
            "feed_url": feed_url,
        })
    return episodes


def read_opml(opml_path):
    root = ET.parse(opml_path).getroot()
    feeds = []
    seen_urls = set()
    for outline in root.iter():
        if local_name(outline.tag) != "outline":
            continue
        feed_url = http_url(outline.get("xmlUrl") or outline.get("xmlurl"))
        if not feed_url or feed_url in seen_urls:
            continue
        show = (outline.get("text") or outline.get("title") or "").strip() or feed_url
        seen_urls.add(feed_url)
        feeds.append((show, feed_url))
    return feeds


def episode_title_key(show, episode):
    return f"title:{' '.join(show.casefold().split())}|{' '.join(episode.casefold().split())}"


def episode_url_key(url):
    parts = urlparse(url.strip())
    if not parts.scheme or not parts.netloc:
        return f"url:{url.strip()}"
    path = parts.path.rstrip("/") or "/"
    return f"url:{urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ''))}"


def load_posted_history(history_dir):
    history = {}
    for manifest_path in sorted(history_dir.glob("poster-*.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"Skipping unreadable poster history {manifest_path}: {error}", file=sys.stderr)
            continue

        generated_at = manifest.get("generated_at", "")
        edition = manifest.get("edition") or generated_at[:10] or "an earlier poster"
        record = {
            "edition": edition,
            "generated_at": generated_at,
            "pdf": manifest.get("pdf", ""),
        }
        for slot in manifest.get("slots", []):
            show = slot.get("show", "").strip()
            episode = slot.get("episode", "").strip()
            if not show or not episode:
                continue
            keys = [episode_title_key(show, episode)]
            if slot.get("url"):
                keys.append(episode_url_key(slot["url"]))
            for key in keys:
                existing = history.get(key)
                if not existing or generated_at >= existing["generated_at"]:
                    history[key] = record
    return history


def scan_feed(show, feed_url, cache_dir, now):
    cache_path = cache_dir / f"{hashlib.sha256(feed_url.encode()).hexdigest()}.xml"
    request = Request(feed_url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
    try:
        with urlopen(request, timeout=20) as response:
            feed_data = response.read(MAX_FEED_BYTES + 1)
        if len(feed_data) > MAX_FEED_BYTES:
            raise ValueError("feed exceeds 12 MB")
        episodes = parse_feed(feed_data, show, feed_url, now)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(feed_data)
        return episodes, "fresh", None
    except (HTTPException, OSError, URLError, ET.ParseError, ValueError) as error:
        if cache_path.is_file():
            try:
                feed_data = cache_path.read_bytes()
                episodes = parse_feed(feed_data, show, feed_url, now)
                return episodes, "cached", str(error)
            except (OSError, ET.ParseError, ValueError) as cache_error:
                return [], "failed", f"{error}; cached feed unusable: {cache_error}"
        return [], "failed", str(error)


def render_page(episodes, feed_count, cached_count, failed_count, generated_at):
    episode_json = json.dumps(episodes, ensure_ascii=False).replace("<", "\\u003c")
    cache_status = f"{cached_count} cached feeds, {failed_count} unavailable"
    posted_count = sum(bool(episode.get("previously_posted")) for episode in episodes)
    page = (
        PAGE_TEMPLATE.replace("__EPISODE_COUNT__", str(len(episodes)))
        .replace("__POSTED_COUNT__", str(posted_count))
        .replace("__FEED_COUNT__", str(feed_count))
        .replace("__GENERATED__", html.escape(generated_at))
        .replace("__CACHE_STATUS__", html.escape(cache_status))
    )
    return page.replace("__EPISODES__", episode_json)


def main():
    if not CONFIG_PATH.is_file():
        raise SystemExit("User config not found; run `just setup` to create user-data/config.json.")
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opml", type=Path, help="OPML path (defaults to user-data/config.json opml_path)")
    args = parser.parse_args()

    opml_path = args.opml or Path(config["opml_path"])
    if not opml_path.is_absolute():
        opml_path = BASE_DIR / opml_path
    if not opml_path.is_file():
        raise SystemExit(
            f"OPML file not found: {opml_path}\n"
            "Place your AntennaPod export there or pass --opml with its path."
        )

    feeds = read_opml(opml_path)
    if not feeds:
        raise SystemExit(f"No RSS feed URLs found in {opml_path}")

    now = datetime.now(timezone.utc)
    cache_dir = Path(config.get("feed_cache_dir", "user-data/cache"))
    if not cache_dir.is_absolute():
        cache_dir = BASE_DIR / cache_dir
    feed_cache_dir = cache_dir / "feeds"

    episodes = []
    statuses = []
    errors = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(scan_feed, show, feed_url, feed_cache_dir, now)
            for show, feed_url in feeds
        ]
        for future in as_completed(futures):
            feed_episodes, status, error = future.result()
            episodes.extend(feed_episodes)
            statuses.append(status)
            if error:
                errors.append(error)

    history_dir = Path(config.get("poster_history_dir", "user-data/history/posters"))
    if not history_dir.is_absolute():
        history_dir = BASE_DIR / history_dir
    posted_history = load_posted_history(history_dir)
    for episode in episodes:
        previous = posted_history.get(episode_url_key(episode["url"]))
        if not previous:
            previous = posted_history.get(episode_title_key(episode["show"], episode["episode"]))
        if previous:
            episode["previously_posted"] = previous

    episodes.sort(key=lambda episode: episode["published_at"], reverse=True)
    cached_count = statuses.count("cached")
    failed_count = statuses.count("failed")
    output_path = Path(config.get("episode_candidates_html", "user-data/episode-candidates.html"))
    if not output_path.is_absolute():
        output_path = BASE_DIR / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_page(episodes, len(feeds), cached_count, failed_count, now.astimezone().strftime("%B %d, %Y %H:%M %Z").replace(" 0", " ")),
        encoding="utf-8",
    )

    print(f"Scanned {len(feeds)} feeds; found {len(episodes)} available episodes.")
    print(f"Review page: {output_path}")
    if cached_count:
        print(f"Used cached responses for {cached_count} feeds.")
    if failed_count:
        print(f"{failed_count} feeds unavailable and had no usable cache.")
    for error in errors:
        print(f"  {error}", file=sys.stderr)


if __name__ == "__main__":
    main()

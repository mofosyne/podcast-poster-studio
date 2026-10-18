"""Fetch recent episodes from the OPML feeds and build a local review page."""

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin, urlparse, urlunsplit
from urllib.request import Request, urlopen

from PIL import Image, ImageOps, UnidentifiedImageError


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "user-data" / "config.json"
MAX_FEED_BYTES = 12 * 1024 * 1024
MAX_ARTWORK_BYTES = 15 * 1024 * 1024
LATEST_EPISODE_ARTWORKS = 3
MAX_DESCRIPTION_CHARS = 400
USER_AGENT = "PodcastPoster/1.0 (local episode browser)"
MAX_WORKERS = 8

class DescriptionTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip_depth += 1
        elif not self.skip_depth and tag in {"br", "div", "li", "p"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        elif not self.skip_depth and tag in {"div", "li", "p"}:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)


PAGE_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Podcast Episode Archive</title>
<style>
:root{color-scheme:dark;--bg:#111412;--panel:#1a1f1c;--line:#303a34;--muted:#9ba79f;--text:#edf2ee;--accent:#4fd1c5;--orange:#f0ad63}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif;padding-bottom:92px}
main{max-width:980px;margin:36px auto;padding:0 22px}
h1{margin:0;font-size:clamp(25px,4vw,38px);letter-spacing:.02em}
.subtitle{color:var(--muted);margin:5px 0 22px}
.status{color:var(--muted);font-size:13px;margin-bottom:18px}
.controls{display:flex;align-items:center;gap:10px;margin-bottom:18px;flex-wrap:wrap}
input[type=search]{flex:1;min-width:0;background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:7px;padding:11px 13px;font:inherit}
.batch-size-control{display:flex;align-items:center;gap:7px;color:var(--muted);font-size:13px;white-space:nowrap}
.batch-size-control input{width:72px;background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:7px;padding:9px;font:inherit}
button{background:var(--accent);color:#10201d;border:0;border-radius:7px;padding:10px 15px;font-weight:700;cursor:pointer}
button:disabled{opacity:.4;cursor:default}
.episode{display:grid;grid-template-columns:26px 64px minmax(0,1fr) auto;gap:12px;align-items:start;padding:15px 14px;border-top:1px solid var(--line)}
.episode:hover{background:#171c19}
.episode input{accent-color:var(--accent);width:17px;height:17px;margin:4px 0 0}
.thumbnail,.thumbnail-placeholder{width:64px;height:64px;border-radius:5px;background:var(--panel)}
.thumbnail{object-fit:cover}
.thumbnail-placeholder{display:grid;place-items:center;color:var(--accent);font-size:28px}
.show{font-weight:700;color:var(--accent)}
.title{font-size:16px;font-weight:600}
a{color:inherit;text-decoration:none}
a:hover{color:var(--accent);text-decoration:underline}
.meta{font-size:13px;color:var(--muted);margin-top:3px}
.description{margin-top:7px;color:var(--muted);font-size:13px}
.description summary{color:var(--accent);cursor:pointer}
.description p{margin:5px 0 0;line-height:1.45}
.episode-tags{margin-top:5px;color:var(--accent);font-size:12px}
.channel-review-details{border:1px solid var(--line);border-radius:7px;background:#171c19;padding:12px;margin:12px 0}
.channel-review-details summary{color:var(--accent);font-weight:700;cursor:pointer}
.channel-review-details label{display:block;color:var(--muted);font-size:13px;margin-top:10px}
.channel-review-details textarea,.channel-review-details input{display:block;width:100%;margin-top:5px;background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:7px;padding:10px;font:inherit}
.channel-review-details textarea{min-height:68px;resize:vertical}
.review-card{padding:16px 0;border-top:1px solid var(--line)}
.review-title{font-weight:700}
.review-meta{font-size:13px;color:var(--muted);margin:3px 0 10px}
.review-card label{display:block;color:var(--muted);font-size:13px}
.review-card textarea,.review-card input{display:block;width:100%;margin-top:5px;background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:7px;padding:10px;font:inherit}
.review-card textarea{min-height:76px;resize:vertical}
.review-count{font-size:12px;color:var(--muted);text-align:right}
.llm-suggest-feedback{font-size:12px;color:var(--muted);margin:3px 0 8px;min-height:1em}
.review-actions{display:flex;justify-content:space-between;gap:10px;margin:20px 0 40px}
.date{font-size:13px;color:var(--orange);white-space:nowrap}
.posted-badge{display:inline-block;margin-left:8px;padding:1px 7px;border:1px solid #8b6841;border-radius:999px;color:var(--orange);font-size:11px;font-weight:600;vertical-align:1px}
.llm-processed-badge{display:inline-block;margin-left:8px;padding:1px 7px;border:1px solid var(--line);border-radius:999px;color:var(--accent);font-size:11px;font-weight:600;vertical-align:1px}
.llm-draft-preview{margin-top:7px;padding:7px 9px;border-left:2px solid var(--accent);background:#171c19}
.llm-draft-preview summary{cursor:pointer;color:var(--accent);font-size:13px}
.llm-draft-preview p{margin:6px 0;color:var(--text);font-size:13px}
.llm-draft-tags{color:var(--muted);font-size:12px}
.bulk-suggestion-status{min-height:1.5em;color:var(--muted);font-size:13px;margin:-10px 0 14px}
.empty{color:var(--muted);padding:28px 14px;border-top:1px solid var(--line)}
.paging{display:flex;justify-content:center;align-items:center;gap:18px;margin:18px 0 34px;color:var(--muted);font-size:13px}
.paging button{background:var(--panel);color:var(--text);border:1px solid var(--line)}
.tray{position:fixed;bottom:0;left:0;right:0;background:#1a201d;border-top:1px solid var(--line);padding:12px 20px;box-shadow:0 -8px 24px #0005}
.tray-inner{max-width:980px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:15px}
#selection{color:var(--muted);font-size:13px}
.toast{position:fixed;bottom:78px;left:50%;transform:translateX(-50%);background:var(--orange);color:#21180e;padding:8px 15px;border-radius:6px;display:none}
.toast.show{display:block}
@media(max-width:600px){main{margin-top:24px;padding:0 14px}.episode{grid-template-columns:22px 52px minmax(0,1fr)}.thumbnail,.thumbnail-placeholder{width:52px;height:52px}.date{grid-column:3}.controls{flex-wrap:wrap}.tray-inner{align-items:flex-start;flex-direction:column}.tray button{width:100%}}
</style>
</head>
<body data-page-version="16">
<main>
  <h1>Podcast episode archive</h1>
  <p class="subtitle">Browse the full episode history available from your subscriptions and choose up to six for the poster.</p>
  <div class="status">__EPISODE_COUNT__ episodes from __FEED_COUNT__ feeds · __POSTED_COUNT__ previously posted · generated __GENERATED__ · __CACHE_STATUS__</div>
  <div class="controls" id="controls"><input id="search" type="search" placeholder="Filter by show or episode title"><button id="clear">Clear selection</button><label class="batch-size-control" id="bulkSuggestionBatchControl" for="bulkSuggestionBatchSize">Batch size <input id="bulkSuggestionBatchSize" type="number" min="1" max="25" step="1" value="10"></label><button id="suggestUnprocessed" type="button" hidden>Process newest 10</button><button id="stopBulkSuggestions" type="button" hidden>Stop after current</button></div>
  <div id="bulkSuggestionStatus" class="bulk-suggestion-status" aria-live="polite">Choose how many of the newest eligible episodes to process per batch (up to 25). Another batch starts only when you choose it.</div>
  <div id="list"></div>
  <div class="paging" id="paging"><button id="previousPage" type="button">Previous</button><span id="pageStatus"></span><button id="nextPage" type="button">Next</button></div>
  <section id="selectionReview" hidden>
    <h2>Edit selection</h2>
    <p class="subtitle">Use optional LLM suggestions for concise summaries and episode tags, then review and edit every draft. Episode details are sent to the configured endpoint only when you request a suggestion.</p>
    <div id="llmSuggestionStatus" class="meta" aria-live="polite">LLM suggestions are unavailable until enabled and configured in Settings.</div>
    <div id="channelReviewList"></div>
    <div id="reviewList"></div>
    <div class="review-actions"><button id="backToEpisodes" type="button">Back to episodes</button><div><button id="downloadSlots" type="button">Download fixed slots</button> <button id="downloadSingle" type="button" hidden>Generate single-episode poster</button></div></div>
  </section>
</main>
<div class="tray" id="tray"><div class="tray-inner"><div><strong id="selection">0 selected</strong><div class="meta">Select episodes, then edit summaries in the Edit selection tab or preview in Poster.</div></div><button id="export" disabled>Edit selection</button></div></div>
<div id="toast" class="toast"></div>
<script>
const EPISODES = __EPISODES__;
const list = document.getElementById("list");
const controls = document.getElementById("controls");
const paging = document.getElementById("paging");
const selectionReview = document.getElementById("selectionReview");
const reviewList = document.getElementById("reviewList");
const channelReviewList = document.getElementById("channelReviewList");
const llmSuggestionStatus = document.getElementById("llmSuggestionStatus");
const tray = document.getElementById("tray");
const search = document.getElementById("search");
const pageStatus = document.getElementById("pageStatus");
const previousPage = document.getElementById("previousPage");
const nextPage = document.getElementById("nextPage");
const PAGE_SIZE = 200;
const MAX_POSTER_SELECTION = 6;
const MAX_BULK_SUGGESTION_BATCH_SIZE = 25;
let currentPage = 0;
const selection = new Set();
const selectionLabel = document.getElementById("selection");
const exportButton = document.getElementById("export");
const toast = document.getElementById("toast");
const suggestUnprocessedButton = document.getElementById("suggestUnprocessed");
const bulkSuggestionBatchControl = document.getElementById("bulkSuggestionBatchControl");
const bulkSuggestionBatchSize = document.getElementById("bulkSuggestionBatchSize");
const stopBulkSuggestionsButton = document.getElementById("stopBulkSuggestions");
const bulkSuggestionStatus = document.getElementById("bulkSuggestionStatus");
const reviewedSummaries = new Map();
const reviewedTags = new Map();
const reviewedTagOverrides = new Set();
const reviewedChannelEditors = new Map();
const reviewedChannelDescriptionOverrides = new Set();
const reviewedChannelTagOverrides = new Set();
let llmSuggestionsReady = false;
let llmSuggestionDisabledReason = "Enable the LLM connection and choose a model in Settings.";
let llmSuggestionVersion = 0;
let llmSuggestionsLoaded = false;
let bulkSuggestionsRunning = false;
let stopBulkSuggestionsRequested = false;
const runningInServer = location.protocol === "http:" && location.hostname === "127.0.0.1" && location.port === "8765";
const downloadSlotsButton = document.getElementById("downloadSlots");
let query = "";

function showToast(message){
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 1800);
}

function defaultPosterSummary(description){
  let summary = (description || "").trim();
  if(summary.length > 400){
    let end = summary.lastIndexOf(" ", 399);
    if(end < 240) end = 399;
    summary = `${summary.slice(0, end).trimEnd()}…`;
  }
  return summary;
}

function parseTags(value){
  const values = Array.isArray(value) ? value : String(value || "").split(",");
  const seen = new Set();
  return values.map(tag => String(tag).trim().replace(/^#+/, "").trim())
    .filter(tag => {
      const key = tag.toLowerCase();
      if(!tag || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function suggestionIsCurrent(episode){
  return Boolean(episode.llm_suggestion && Number(episode.llm_suggestion.suggestion_version) === llmSuggestionVersion);
}

function updateSuggestionButtons(){
  for(const button of document.querySelectorAll(".llm-suggest")){
    const episode = EPISODES[Number(button.dataset.episodeIndex)];
    const version = Number(episode?.llm_suggestion?.suggestion_version || 0);
    button.textContent = version > 0
      ? (version === llmSuggestionVersion ? "Regenerate summary + tags" : "Update old draft")
      : "Suggest summary + tags";
    button.disabled = !llmSuggestionsReady;
    button.title = llmSuggestionsReady ? "Draft a summary and episode-specific tag suggestions" : llmSuggestionDisabledReason;
  }
  updateBulkSuggestionControls();
}

function updateBulkSuggestionControls(){
  suggestUnprocessedButton.hidden = !runningInServer;
  bulkSuggestionBatchControl.hidden = !runningInServer;
  stopBulkSuggestionsButton.hidden = !bulkSuggestionsRunning;
  stopBulkSuggestionsButton.disabled = stopBulkSuggestionsRequested;
  const pending = EPISODES.filter(episode => !suggestionIsCurrent(episode)).length;
  const maximum = Math.min(MAX_BULK_SUGGESTION_BATCH_SIZE, pending);
  let requested = Number.parseInt(bulkSuggestionBatchSize.value, 10);
  if(!Number.isFinite(requested) || requested < 1) requested = Math.min(10, Math.max(1, maximum));
  requested = Math.min(requested, Math.max(1, maximum));
  bulkSuggestionBatchSize.max = String(Math.max(1, maximum));
  bulkSuggestionBatchSize.value = String(requested);
  bulkSuggestionBatchSize.disabled = !llmSuggestionsLoaded || pending === 0 || bulkSuggestionsRunning;
  suggestUnprocessedButton.textContent = !llmSuggestionsLoaded
    ? "Loading saved drafts…"
    : pending
      ? `Process newest ${Math.min(requested, pending)} of ${pending}`
      : "All episodes have current drafts";
  suggestUnprocessedButton.disabled = !llmSuggestionsLoaded || !llmSuggestionsReady || pending === 0 || bulkSuggestionsRunning;
}

function applyLlmSettings(settings){
  llmSuggestionsReady = settings?.enabled === true;
  llmSuggestionDisabledReason = settings?.reason || "Enable the LLM connection and choose a model in Settings.";
  llmSuggestionStatus.hidden = llmSuggestionsReady;
  llmSuggestionStatus.textContent = llmSuggestionsReady
    ? "LLM suggestions are ready."
    : `LLM suggestions unavailable: ${llmSuggestionDisabledReason}`;
  updateSuggestionButtons();
}

function suggestionRequestEpisode(index, currentSummary="", episodeTags=null){
  const episode = EPISODES[index];
  const channel = reviewedChannelEditors.get(episode.feed_url);
  return {
    url:episode.url,
    show:episode.show,
    title:episode.episode,
    description:episode.description || "",
    channel_description:channel ? channel.description.value : (episode.channel_description || episode.feed_description || ""),
    channel_tags:parseTags(channel ? channel.tags.value : (episode.tags || [])),
    episode_tags:episodeTags || episode.llm_suggestion?.tags || episode.tags || [],
    current_summary:currentSummary || episode.llm_suggestion?.summary || "",
  };
}

async function requestEpisodeSuggestion(index, currentSummary="", episodeTags=null){
  const response = await fetch("/api/llm/suggest", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({episode:suggestionRequestEpisode(index, currentSummary, episodeTags)})
  });
  const result = await response.json();
  if(!response.ok) throw new Error(result.error || "LLM suggestion failed.");
  EPISODES[index].llm_suggestion = {
    summary:result.summary,
    tags:result.tags,
    suggestion_version:result.suggestion_version || llmSuggestionVersion,
    processed_at:result.processed_at || new Date().toISOString(),
  };
  return result;
}

async function suggestEpisode(index, summaryInput, tagsInput, summaryCount, button, feedback){
  feedback.textContent = "Requesting a draft from the configured model…";
  button.disabled = true;
  button.textContent = "Generating suggestions…";
  try{
    const result = await requestEpisodeSuggestion(index, summaryInput.value, parseTags(tagsInput.value));
    summaryInput.value = result.summary;
    summaryCount.textContent = `${summaryInput.value.length}/400`;
    tagsInput.value = result.tags.join(", ");
    reviewedTagOverrides.add(index);
    reportSelection();
    render();
    feedback.textContent = "Draft suggestions saved. Review and edit them before generating the poster.";
    showToast("Draft suggestions saved. Review before generating the poster.");
  }catch(error){
    feedback.textContent = `Suggestion failed: ${error.message} See Settings → Recent LLM diagnostics for details.`;
    showToast(`Could not get suggestions: ${error.message}`);
  }finally{
    updateSuggestionButtons();
  }
}

async function processUnprocessedEpisodes(){
  const pending = EPISODES.map((episode, index) => ({episode, index}))
    .filter(({episode}) => !suggestionIsCurrent(episode))
    .sort((left, right) => {
      const leftDate = Date.parse(left.episode.published_at || "") || 0;
      const rightDate = Date.parse(right.episode.published_at || "") || 0;
      return rightDate - leftDate;
    });
  const pendingTotal = pending.length;
  const batchSize = Math.max(1, Math.min(
    MAX_BULK_SUGGESTION_BATCH_SIZE,
    pendingTotal,
    Number.parseInt(bulkSuggestionBatchSize.value, 10) || 10
  ));
  const pendingIndices = pending.slice(0, batchSize).map(({index}) => index);
  if(!pendingIndices.length || bulkSuggestionsRunning) return;
  const approved = window.confirm(
    `Process only the newest ${pendingIndices.length} of ${pendingTotal} unprocessed or older-version episodes? ` +
    "This sends episode descriptions and channel context to the configured model, one at a time. Another batch will not start automatically."
  );
  if(!approved) return;

  bulkSuggestionsRunning = true;
  stopBulkSuggestionsRequested = false;
  let completed = 0;
  let failed = 0;
  let lastError = "";
  updateBulkSuggestionControls();
  try{
    for(const [position, index] of pendingIndices.entries()){
      if(stopBulkSuggestionsRequested) break;
      const episode = EPISODES[index];
      bulkSuggestionStatus.textContent = `Processing ${position + 1} of ${pendingIndices.length}: ${episode.show} — ${episode.episode}`;
      try{
        await requestEpisodeSuggestion(index);
        completed += 1;
      }catch(error){
        failed += 1;
        lastError = error.message;
      }
      updateBulkSuggestionControls();
    }
  }finally{
    bulkSuggestionsRunning = false;
    render();
    const stopped = stopBulkSuggestionsRequested;
    const remaining = EPISODES.filter(episode => !suggestionIsCurrent(episode)).length;
    const stoppingText = stopped ? " Stopped after the current episode." : "";
    bulkSuggestionStatus.textContent = `${completed} saved, ${failed} failed.${stoppingText} ${remaining} episodes remain for later batches.${lastError ? ` Last error: ${lastError}` : ""}`;
    updateBulkSuggestionControls();
  }
}

async function loadLlmSuggestions(){
  try{
    const response = await fetch("/api/llm/suggestions");
    const result = await response.json();
    if(!response.ok) throw new Error(result.error || "Could not load saved LLM drafts.");
    llmSuggestionVersion = Number(result.version || 1);
    const suggestions = result.suggestions && typeof result.suggestions === "object" ? result.suggestions : {};
    for(const episode of EPISODES){
      const saved = suggestions[episode.url];
      if(saved && typeof saved.summary === "string" && Array.isArray(saved.tags)) episode.llm_suggestion = saved;
    }
    llmSuggestionsLoaded = true;
    render();
  }catch(error){
    bulkSuggestionStatus.textContent = `Could not load saved LLM drafts: ${error.message}`;
  }
}

function buildSelectedSlots(){
  return [...selection].map(index => {
    const episode = EPISODES[index];
    const slot = {
      type:"fixed",
      show:episode.show,
      episode:episode.episode,
      date:episode.date,
      url:episode.url,
      feed_url:episode.feed_url
    };
    const summaryField = reviewedSummaries.get(index);
    const summary = (summaryField ? summaryField.value : defaultPosterSummary(episode.description)).trim();
    if(summary) slot.summary = summary;
    if(episode.channel_description !== undefined) slot.channel_description = episode.channel_description;
    const tagsField = reviewedTags.get(index);
    const tags = parseTags(tagsField ? tagsField.value : (episode.tags || []));
    if(tags.length || reviewedTagOverrides.has(index) || reviewedChannelTagOverrides.has(episode.feed_url)) slot.tags = tags;
    if(episode.duration) slot.duration = episode.duration;
    if(episode.artwork_path) slot.artwork_path = episode.artwork_path;
    return slot;
  });
}

function reportSelection(){
  if(runningInServer){
    window.parent.postMessage({type:"candidate-selection", slots:buildSelectedSlots()}, window.location.origin);
  }
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
      if(checkbox.checked && selection.size >= MAX_POSTER_SELECTION){
        checkbox.checked = false;
        showToast(`Select up to ${MAX_POSTER_SELECTION} episodes for one poster.`);
        return;
      }
      if(checkbox.checked){
        selection.add(index);
        if(episode.previously_posted){
          const status = episode.previously_posted.print_status;
          const message = status === "not_printed"
            ? `Included in an unprinted poster: ${episode.previously_posted.edition}.`
            : `Already appeared in ${episode.previously_posted.edition}.`;
          showToast(message);
        }
      } else selection.delete(index);
      updateSelection();
    });
    let thumbnail;
    if(episode.artwork){
      thumbnail = document.createElement("img");
      thumbnail.className = "thumbnail";
      thumbnail.src = episode.artwork;
      thumbnail.alt = `Cover art for ${episode.show}`;
      thumbnail.loading = "lazy";
      thumbnail.decoding = "async";
    } else {
      thumbnail = document.createElement("div");
      thumbnail.className = "thumbnail-placeholder";
      thumbnail.setAttribute("aria-hidden", "true");
      thumbnail.textContent = "♫";
    }
    const body = document.createElement("div");
    const show = document.createElement("div");
    show.className = "show";
    show.textContent = episode.show;
    if(episode.previously_posted){
      const badge = document.createElement("span");
      badge.className = "posted-badge";
      const status = episode.previously_posted.print_status;
      const label = status === "not_printed" ? "Generated, not marked printed" : status === "unknown" ? "Earlier poster" : "Previously printed";
      badge.textContent = `${label} · ${episode.previously_posted.edition}`;
      show.append(badge);
    }
    if(episode.llm_suggestion){
      const badge = document.createElement("span");
      badge.className = "llm-processed-badge";
      const version = Number(episode.llm_suggestion.suggestion_version || 0);
      badge.textContent = version === llmSuggestionVersion ? `AI processed · v${version}` : `AI processed · v${version} · update available`;
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
    meta.textContent = episode.duration ? `${episode.duration} listen` : "Duration not listed";
    body.append(show, title, meta);
    if(Array.isArray(episode.tags) && episode.tags.length){
      const tags = document.createElement("div");
      tags.className = "episode-tags";
      tags.textContent = episode.tags.map(tag => `#${tag}`).join(" ");
      body.append(tags);
    }
    if(episode.llm_suggestion){
      const draftDetails = document.createElement("details");
      draftDetails.className = "llm-draft-preview";
      const draftHeading = document.createElement("summary");
      const draftSummaryText = typeof episode.llm_suggestion.summary === "string" ? episode.llm_suggestion.summary : "";
      const draftSnippet = draftSummaryText.length > 120 ? `${draftSummaryText.slice(0, 120).trimEnd()}…` : draftSummaryText;
      draftHeading.textContent = `AI draft: ${draftSnippet || "No summary text."}`;
      const draftSummary = document.createElement("p");
      draftSummary.textContent = draftSummaryText;
      const draftTags = document.createElement("div");
      draftTags.className = "llm-draft-tags";
      const savedTags = Array.isArray(episode.llm_suggestion.tags) ? episode.llm_suggestion.tags : [];
      draftTags.textContent = savedTags.length ? savedTags.map(tag => `#${tag}`).join(" ") : "No episode tags suggested.";
      draftDetails.append(draftHeading, draftSummary, draftTags);
      body.append(draftDetails);
    }
    const channelDescription = episode.channel_description || episode.feed_description;
    if(channelDescription){
      const details = document.createElement("details");
      details.className = "description channel-description";
      const summary = document.createElement("summary");
      summary.textContent = "Channel description";
      const description = document.createElement("p");
      description.textContent = channelDescription;
      details.append(summary, description);
      body.append(details);
    }
    if(episode.description){
      const details = document.createElement("details");
      details.className = "description";
      const summary = document.createElement("summary");
      summary.textContent = "Episode description";
      const description = document.createElement("p");
      description.textContent = episode.description;
      details.append(summary, description);
      body.append(details);
    }
    const date = document.createElement("div");
    date.className = "date";
    date.textContent = new Date(episode.published_at).toLocaleDateString(undefined, {year:"numeric", month:"short", day:"numeric"});
    row.append(checkbox, thumbnail, body, date);
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
  if(downloadSingleButton) downloadSingleButton.hidden = true;
  updateBulkSuggestionControls();
  reportSelection();
}

search.addEventListener("input", event => { query = event.target.value; currentPage = 0; render(); });
previousPage.addEventListener("click", () => { currentPage -= 1; render(); });
nextPage.addEventListener("click", () => { currentPage += 1; render(); });
document.getElementById("clear").addEventListener("click", () => { selection.clear(); render(); });
function openSelectionReview(){
  const previousSummaries = new Map(
    [...reviewedSummaries].map(([index, textarea]) => [index, textarea.value])
  );
  const previousTags = new Map(
    [...reviewedTags].filter(([index]) => reviewedTagOverrides.has(index)).map(([index, input]) => [index, input.value])
  );
  reviewedSummaries.clear();
  reviewedTags.clear();
  reviewedChannelEditors.clear();
  channelReviewList.replaceChildren();
  reviewList.replaceChildren();

  const channels = new Map();
  for(const index of selection){
    const episode = EPISODES[index];
    if(!channels.has(episode.feed_url)) channels.set(episode.feed_url, {show:episode.show, indices:[]});
    channels.get(episode.feed_url).indices.push(index);
  }
  for(const [feedUrl, group] of channels){
    const firstEpisode = EPISODES[group.indices[0]];
    const details = document.createElement("details");
    details.className = "channel-review-details";
    details.open = false;
    const heading = document.createElement("summary");
    heading.textContent = `Channel details — ${group.show}`;
    const descriptionLabel = document.createElement("label");
    descriptionLabel.textContent = "Channel description / editorial note (up to 400 characters)";
    const descriptionInput = document.createElement("textarea");
    descriptionInput.maxLength = 400;
    descriptionInput.value = firstEpisode.channel_description ?? firstEpisode.feed_description ?? "";
    descriptionLabel.append(descriptionInput);

    const tagsLabel = document.createElement("label");
    tagsLabel.textContent = "Common channel tags (suggestions preloaded for episode tags)";
    const tagsInput = document.createElement("input");
    tagsInput.type = "text";
    tagsInput.maxLength = 500;
    tagsInput.value = (firstEpisode.tags || []).join(", ");
    tagsLabel.append(tagsInput);

    descriptionInput.addEventListener("input", () => {
      reviewedChannelDescriptionOverrides.add(feedUrl);
      for(const episode of EPISODES){
        if(episode.feed_url === feedUrl) episode.channel_description = descriptionInput.value;
      }
      reportSelection();
    });
    tagsInput.addEventListener("input", () => {
      reviewedChannelTagOverrides.add(feedUrl);
      const tags = parseTags(tagsInput.value);
      for(const index of group.indices){
        EPISODES[index].tags = tags;
        const episodeTagsInput = reviewedTags.get(index);
        if(episodeTagsInput && !reviewedTagOverrides.has(index)) episodeTagsInput.value = tags.join(", ");
      }
      reportSelection();
    });
    details.append(heading, descriptionLabel, tagsLabel);
    channelReviewList.append(details);
    reviewedChannelEditors.set(feedUrl, {description:descriptionInput, tags:tagsInput});
  }

  for(const index of selection){
    const episode = EPISODES[index];
    const card = document.createElement("div");
    card.className = "review-card";
    const title = document.createElement("div");
    title.className = "review-title";
    title.textContent = `${episode.show} — ${episode.episode}`;
    const meta = document.createElement("div");
    meta.className = "review-meta";
    meta.textContent = `${episode.date} · ${episode.duration || "Duration not listed"}`;
    const suggestButton = document.createElement("button");
    suggestButton.type = "button";
    suggestButton.className = "llm-suggest";
    suggestButton.dataset.episodeIndex = String(index);
    suggestButton.textContent = "Suggest summary + tags";
    suggestButton.hidden = !runningInServer;
    suggestButton.disabled = !llmSuggestionsReady;
    suggestButton.title = llmSuggestionDisabledReason;
    const suggestionFeedback = document.createElement("div");
    suggestionFeedback.className = "llm-suggest-feedback";
    suggestionFeedback.setAttribute("aria-live", "polite");
    const tagsLabel = document.createElement("label");
    tagsLabel.textContent = "Episode tags (edit these suggestions for this episode only)";
    const tagsInput = document.createElement("input");
    tagsInput.type = "text";
    tagsInput.maxLength = 500;
    tagsInput.value = previousTags.get(index) ?? (episode.llm_suggestion?.tags || episode.tags || []).join(", ");
    if(episode.llm_suggestion) reviewedTagOverrides.add(index);
    tagsInput.addEventListener("input", () => {
      reviewedTagOverrides.add(index);
      reportSelection();
    });
    tagsLabel.append(tagsInput);
    const label = document.createElement("label");
    label.textContent = "Short poster summary (optional, up to 400 characters)";
    const textarea = document.createElement("textarea");
    textarea.maxLength = 400;
    textarea.value = previousSummaries.get(index) ?? episode.llm_suggestion?.summary ?? defaultPosterSummary(episode.description);
    const count = document.createElement("div");
    count.className = "review-count";
    count.textContent = `${textarea.value.length}/400`;
    textarea.addEventListener("input", () => {
      count.textContent = `${textarea.value.length}/400`;
      reportSelection();
    });
    label.append(textarea);
    suggestButton.addEventListener("click", () => suggestEpisode(index, textarea, tagsInput, count, suggestButton, suggestionFeedback));
    card.append(title, meta, suggestButton, suggestionFeedback, tagsLabel, label, count);
    reviewList.append(card);
    reviewedTags.set(index, tagsInput);
    reviewedSummaries.set(index, textarea);
  }
  controls.hidden = true;
  list.hidden = true;
  paging.hidden = true;
  tray.hidden = true;
  selectionReview.hidden = false;
  updateSuggestionButtons();
  reportSelection();
  window.scrollTo(0, 0);
}

function closeSelectionReview(){
  selectionReview.hidden = true;
  controls.hidden = false;
  list.hidden = false;
  paging.hidden = false;
  tray.hidden = false;
}

async function downloadSelectedSlots(layout="list"){
  const chosen = buildSelectedSlots();
  if(runningInServer){
    downloadSlotsButton.disabled = true;
    downloadSingleButton.disabled = true;
    try{
      const response = await fetch("/api/generate", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({slots:chosen, layout})
      });
      const result = await response.json();
      if(!response.ok) throw new Error(result.error || "Poster generation failed.");
      showToast(`${layout === "single" ? "Single-episode" : "List"} poster generated and archived.`);
      window.parent.postMessage({type:"poster-generated"}, window.location.origin);
    }catch(error){
      showToast(error.message);
    }finally{
      downloadSlotsButton.disabled = false;
      downloadSingleButton.disabled = false;
    }
    return;
  }

  const blob = new Blob([JSON.stringify(chosen, null, 2)], {type:"application/json"});
  const link = document.createElement("a");
  const downloadUrl = URL.createObjectURL(blob);
  link.href = downloadUrl;
  link.download = "selected-slots.json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
  showToast("Reviewed slots exported.");
}

function applyChannelMetadata(metadata){
  for(const [index, episode] of EPISODES.entries()){
    const channel = metadata[episode.feed_url] || {};
    if(!reviewedChannelDescriptionOverrides.has(episode.feed_url)){
      episode.channel_description = channel.channel_description || episode.feed_description || "";
    }
    if(!reviewedChannelTagOverrides.has(episode.feed_url)){
      episode.tags = Array.isArray(channel.tags) ? channel.tags : [];
    }
    const tagsField = reviewedTags.get(index);
    if(tagsField && !reviewedTagOverrides.has(index) && !reviewedChannelTagOverrides.has(episode.feed_url)){
      tagsField.value = episode.tags.join(", ");
    }
  }
  for(const [feedUrl, editors] of reviewedChannelEditors){
    const episode = EPISODES.find(item => item.feed_url === feedUrl);
    if(!episode) continue;
    if(!reviewedChannelDescriptionOverrides.has(feedUrl)){
      editors.description.value = episode.channel_description ?? episode.feed_description ?? "";
    }
    if(!reviewedChannelTagOverrides.has(feedUrl)) editors.tags.value = (episode.tags || []).join(", ");
  }
  render();
}

function normalizeHistoryUrl(value){
  try{
    const url = new URL(value);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    return `url:${url.protocol.toLowerCase()}//${url.host.toLowerCase()}${path}${url.search}`;
  }catch(error){ return `url:${(value || "").trim()}`; }
}

function normalizeHistoryTitle(show, title){
  const normalize = value => (value || "").trim().toLowerCase().replace(/\s+/g, " ");
  return `title:${normalize(show)}|${normalize(title)}`;
}

function applyPosterHistory(records){
  const byUrl = new Map();
  const byTitle = new Map();
  for(const record of records){
    const status = record.print_status;
    const posted = {edition:record.edition, generated_at:record.generated_at, print_status:status};
    if(record.url){
      const key = normalizeHistoryUrl(record.url);
      if(!byUrl.has(key)) byUrl.set(key, posted);
    }
    const titleKey = normalizeHistoryTitle(record.show, record.episode);
    if(!byTitle.has(titleKey)) byTitle.set(titleKey, posted);
  }
  let postedCount = 0;
  for(const episode of EPISODES){
    const posted = byUrl.get(normalizeHistoryUrl(episode.url))
      || byTitle.get(normalizeHistoryTitle(episode.show, episode.episode));
    if(posted){
      episode.previously_posted = posted;
      postedCount += 1;
    } else delete episode.previously_posted;
  }
  const status = document.querySelector(".status");
  if(status){
    status.textContent = status.textContent.replace(
      / · \d+ previously posted · /,
      ` · ${postedCount} previously posted · `
    );
  }
  render();
}

const downloadSingleButton = document.getElementById("downloadSingle");
if(runningInServer){
  exportButton.hidden = true;
  downloadSlotsButton.hidden = true;
  downloadSingleButton.hidden = true;
  downloadSlotsButton.parentElement.hidden = true;
  window.addEventListener("message", event => {
    if(event.origin !== location.origin || event.source !== window.parent) return;
    if(event.data?.type === "open-selection-review") openSelectionReview();
    if(event.data?.type === "close-selection-review") closeSelectionReview();
    if(event.data?.type === "poster-history" && Array.isArray(event.data.records)) applyPosterHistory(event.data.records);
    if(event.data?.type === "channel-metadata" && event.data.metadata && typeof event.data.metadata === "object") applyChannelMetadata(event.data.metadata);
    if(event.data?.type === "llm-settings" && event.data.settings && typeof event.data.settings === "object") applyLlmSettings(event.data.settings);
  });
} else {
  downloadSingleButton.hidden = true;
  exportButton.addEventListener("click", openSelectionReview);
}
document.getElementById("downloadSlots").addEventListener("click", () => downloadSelectedSlots("list"));
document.getElementById("backToEpisodes").addEventListener("click", () => {
  closeSelectionReview();
  if(runningInServer) window.parent.postMessage({type:"show-episodes-tab"}, window.location.origin);
});
bulkSuggestionBatchSize.addEventListener("input", updateBulkSuggestionControls);
suggestUnprocessedButton.addEventListener("click", processUnprocessedEpisodes);
stopBulkSuggestionsButton.addEventListener("click", () => {
  stopBulkSuggestionsRequested = true;
  stopBulkSuggestionsButton.disabled = true;
  bulkSuggestionStatus.textContent = "Stopping after the current episode finishes…";
});
render();
if(runningInServer) loadLlmSuggestions();
</script>
</body>
</html>
"""


def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


def http_url(value, base_url=""):
    if not value or not value.strip():
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


def format_duration(value):
    value = value.strip()
    if not value:
        return None

    seconds = None
    if value.isdecimal():
        seconds = int(value)
    elif value.upper().startswith("P"):
        match = re.fullmatch(
            r"P(?:(\d+(?:\.\d+)?)D)?(?:T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?)?",
            value.upper(),
        )
        if match:
            days, hours, minutes, remainder = (float(part or 0) for part in match.groups())
            seconds = days * 86400 + hours * 3600 + minutes * 60 + remainder
    elif re.fullmatch(r"\d+(?::\d+){1,2}", value):
        parts = [int(part) for part in value.split(":")]
        if len(parts) == 2:
            seconds = parts[0] * 60 + parts[1]
        else:
            seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]

    if not seconds or seconds < 0:
        return None
    total_seconds = round(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours and minutes:
        return f"{hours} hr {minutes} min"
    if hours:
        return f"{hours} hr"
    if minutes:
        return f"{minutes} min"
    return f"{seconds} sec"


def episode_duration(item):
    for child in item:
        if local_name(child.tag) == "duration":
            duration = format_duration("".join(child.itertext()))
            if duration:
                return duration
    return None


def episode_description(item):
    for name in ("summary", "description", "subtitle", "encoded", "content"):
        for child in item:
            if local_name(child.tag) != name:
                continue
            parser = DescriptionTextParser()
            parser.feed("".join(child.itertext()))
            description = " ".join("".join(parser.parts).split())
            if description:
                if len(description) > MAX_DESCRIPTION_CHARS:
                    cutoff = description.rfind(" ", 0, MAX_DESCRIPTION_CHARS)
                    if cutoff < MAX_DESCRIPTION_CHARS * 0.6:
                        cutoff = MAX_DESCRIPTION_CHARS - 1
                    return description[:cutoff].rstrip() + "…"
                return description
    return None


def feed_channel_description(root):
    channel = next((node for node in root.iter() if local_name(node.tag) in {"channel", "feed"}), root)
    for child in channel:
        if local_name(child.tag) not in {"description", "subtitle", "summary"}:
            continue
        parser = DescriptionTextParser()
        parser.feed("".join(child.itertext()))
        description = " ".join("".join(parser.parts).split())
        if not description:
            continue
        if len(description) > MAX_DESCRIPTION_CHARS:
            cutoff = description.rfind(" ", 0, MAX_DESCRIPTION_CHARS)
            if cutoff < MAX_DESCRIPTION_CHARS * 0.6:
                cutoff = MAX_DESCRIPTION_CHARS - 1
            description = description[:cutoff].rstrip() + "…"
        return description
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


def episode_artwork_url(item, feed_url):
    for node in item.iter():
        name = local_name(node.tag)
        image_url = None
        if name in {"image", "thumbnail"}:
            image_url = node.get("href") or node.get("url") or node.get("src")
            if not image_url or not image_url.strip():
                image_url = next(
                    (child.text for child in node if local_name(child.tag) == "url" and child.text and child.text.strip()),
                    None,
                )
            if not image_url or not image_url.strip():
                image_url = node.text
        elif name == "content" and (
            node.get("medium", "").lower() == "image"
            or node.get("type", "").lower().startswith("image/")
        ):
            image_url = node.get("url")
        elif name == "link" and node.get("rel", "").lower() == "enclosure":
            if node.get("type", "").lower().startswith("image/"):
                image_url = node.get("href")
        resolved = http_url(image_url, feed_url)
        if resolved:
            return resolved
    return None


def feed_artwork_url(root, feed_url):
    channel = next((node for node in root.iter() if local_name(node.tag) == "channel"), root)

    for node in channel:
        name = local_name(node.tag)
        if name in {"image", "logo", "icon"}:
            image_url = node.get("href") or node.get("url")
            if not image_url:
                image_url = next(
                    (child.text for child in node if local_name(child.tag) == "url" and child.text),
                    node.text,
                )
            resolved = http_url(image_url, feed_url)
            if resolved:
                return resolved
        elif name == "images":
            for image in node:
                if local_name(image.tag) == "image":
                    resolved = http_url(image.get("href") or image.text, feed_url)
                    if resolved:
                        return resolved

    return None


def latest_episode_artwork_sources(episodes):
    episodes_by_feed = {}
    for episode in episodes:
        episodes_by_feed.setdefault(episode["feed_url"], []).append(episode)

    sources = {}
    for feed_episodes in episodes_by_feed.values():
        latest = sorted(
            feed_episodes,
            key=lambda episode: episode["published_at"],
            reverse=True,
        )[:LATEST_EPISODE_ARTWORKS]
        for episode in latest:
            image_url = episode.get("episode_artwork_url")
            if image_url and image_url != episode.get("artwork_url"):
                sources.setdefault(image_url, episode["show"])
    return sources


def cache_artwork_image(image_url, cache_path):
    if cache_path.is_file():
        return cache_path, "cached"
    if not image_url:
        return None, "unavailable"

    request = Request(image_url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=20) as response:
            image_data = response.read(MAX_ARTWORK_BYTES + 1)
        if len(image_data) > MAX_ARTWORK_BYTES:
            raise ValueError("artwork image is larger than 15 MB")
        with Image.open(BytesIO(image_data)) as source:
            artwork = ImageOps.fit(source.convert("RGBA"), (512, 512))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        artwork.save(cache_path, format="PNG", optimize=True)
        return cache_path, "downloaded"
    except (OSError, URLError, ValueError, UnidentifiedImageError):
        return None, "unavailable"


def cache_feed_artwork(feed_url, image_url, cache_dir):
    cache_path = cache_dir / f"{hashlib.sha256(feed_url.encode()).hexdigest()}-v2.png"
    return cache_artwork_image(image_url, cache_path)


def cache_episode_artwork(image_url, cache_dir):
    digest = hashlib.sha256(image_url.encode()).hexdigest()
    cache_path = cache_dir / f"episode-{digest}-v2.png"
    return cache_artwork_image(image_url, cache_path)


def parse_feed(feed_data, show, feed_url, now):
    root = ET.fromstring(feed_data)
    artwork_url = feed_artwork_url(root, feed_url)
    channel_description = feed_channel_description(root)
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
        description = episode_description(node)
        duration = episode_duration(node)
        episode_image_url = episode_artwork_url(node, feed_url)
        if not title or not published_at or not url or published_at > now:
            continue
        episode = {
            "show": show,
            "episode": title,
            "date": f"{published_at.strftime('%B')} {published_at.day}, {published_at.year}",
            "published_at": published_at.isoformat(),
            "url": url,
            "feed_url": feed_url,
            "artwork_url": artwork_url,
            "episode_artwork_url": episode_image_url,
        }
        if channel_description:
            episode["feed_description"] = channel_description
            episode["channel_description"] = channel_description
        if description:
            episode["description"] = description
        if duration:
            episode["duration"] = duration
        episodes.append(episode)
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
        if "printed_at" not in manifest:
            print_status = "unknown"
        else:
            print_status = "printed" if manifest.get("printed_at") else "not_printed"
        record = {
            "edition": edition,
            "generated_at": generated_at,
            "pdf": manifest.get("pdf", ""),
            "printed_at": manifest.get("printed_at"),
            "print_status": print_status,
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
    print(f"Scanning {len(feeds)} feeds with up to {MAX_WORKERS} workers...", flush=True)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(scan_feed, show, feed_url, feed_cache_dir, now): show
            for show, feed_url in feeds
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            feed_episodes, status, error = future.result()
            episodes.extend(feed_episodes)
            statuses.append(status)
            show = futures[future]
            print(
                f"[{completed}/{len(feeds)}] {show}: {len(feed_episodes)} episodes ({status})",
                flush=True,
            )
            if error:
                errors.append(f"{show}: {error}")

    subscription_metadata = config.get("subscription_metadata", {})
    if not isinstance(subscription_metadata, dict):
        subscription_metadata = {}
    for episode in episodes:
        metadata = subscription_metadata.get(episode["feed_url"], {})
        if not isinstance(metadata, dict):
            metadata = {}
        channel_description = metadata.get("channel_description")
        if isinstance(channel_description, str) and channel_description.strip():
            episode["channel_description"] = channel_description.strip()[:MAX_DESCRIPTION_CHARS]
        tags = metadata.get("tags", [])
        if isinstance(tags, list):
            episode["tags"] = [tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()][:12]

    artwork_sources = {}
    for episode in episodes:
        artwork_sources.setdefault(
            episode["feed_url"],
            (episode["show"], episode.get("artwork_url")),
        )

    artwork_cache_dir = cache_dir / "artwork"
    artwork_paths = {}
    artwork_counts = {"downloaded": 0, "cached": 0, "unavailable": 0}
    if artwork_sources:
        print(f"Caching channel artwork for {len(artwork_sources)} shows...", flush=True)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            artwork_futures = {
                executor.submit(cache_feed_artwork, feed_url, image_url, artwork_cache_dir): (feed_url, show)
                for feed_url, (show, image_url) in artwork_sources.items()
            }
            for completed, future in enumerate(as_completed(artwork_futures), start=1):
                feed_url, show = artwork_futures[future]
                artwork_path, status = future.result()
                artwork_counts[status] += 1
                if artwork_path:
                    artwork_paths[feed_url] = artwork_path
                print(f"[artwork {completed}/{len(artwork_sources)}] {show}: {status}", flush=True)

    episode_artwork_sources = latest_episode_artwork_sources(episodes)

    episode_artwork_paths = {}
    episode_artwork_counts = {"downloaded": 0, "cached": 0, "unavailable": 0}
    if episode_artwork_sources:
        print(
            f"Caching episode artwork for the latest {LATEST_EPISODE_ARTWORKS} episodes "
            f"per show ({len(episode_artwork_sources)} unique images)...",
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            episode_artwork_futures = {
                executor.submit(cache_episode_artwork, image_url, artwork_cache_dir): (image_url, show)
                for image_url, show in episode_artwork_sources.items()
            }
            for completed, future in enumerate(as_completed(episode_artwork_futures), start=1):
                image_url, show = episode_artwork_futures[future]
                artwork_path, status = future.result()
                episode_artwork_counts[status] += 1
                if artwork_path:
                    episode_artwork_paths[image_url] = artwork_path
                print(f"[episode art {completed}/{len(episode_artwork_sources)}] {show}: {status}", flush=True)

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
    for episode in episodes:
        episode.pop("artwork_url", None)
        episode_artwork_url = episode.pop("episode_artwork_url", None)
        channel_artwork_path = artwork_paths.get(episode["feed_url"])
        if channel_artwork_path:
            try:
                episode["channel_artwork_path"] = Path(os.path.relpath(channel_artwork_path, BASE_DIR)).as_posix()
            except ValueError:
                pass
        artwork_path = episode_artwork_paths.get(episode_artwork_url) or channel_artwork_path
        if artwork_path:
            try:
                episode["artwork"] = Path(os.path.relpath(artwork_path, output_path.parent)).as_posix()
            except ValueError:
                episode["artwork"] = artwork_path.as_uri()
            try:
                episode["artwork_path"] = Path(os.path.relpath(artwork_path, BASE_DIR)).as_posix()
            except ValueError:
                pass
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
    if artwork_sources:
        print(
            f"Channel artwork: {artwork_counts['downloaded']} downloaded, "
            f"{artwork_counts['cached']} cached, "
            f"{artwork_counts['unavailable']} unavailable."
        )
    if episode_artwork_sources:
        print(
            f"Episode artwork: {episode_artwork_counts['downloaded']} downloaded, "
            f"{episode_artwork_counts['cached']} cached, "
            f"{episode_artwork_counts['unavailable']} unavailable."
        )
    for error in errors:
        print(f"  {error}", file=sys.stderr)


if __name__ == "__main__":
    main()

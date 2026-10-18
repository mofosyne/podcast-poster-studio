APP_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Podcast Poster Studio</title>
<style>
:root{color-scheme:dark;--bg:#111412;--panel:#1a1f1c;--line:#303a34;--muted:#9ba79f;--text:#edf2ee;--accent:#4fd1c5;--orange:#f0ad63}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}
header{display:block;padding:12px 24px 0;border-bottom:1px solid var(--line);background:#171c19;position:sticky;top:0;z-index:2}
.header-row{display:flex;align-items:center;justify-content:space-between;gap:16px}
h1{font-size:22px;margin:0}
h2{font-size:17px;margin:0 0 10px}
.controls{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
button,.upload,select{border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--text);padding:8px 12px;font:inherit;cursor:pointer}
button.primary{background:var(--accent);color:#10201d;border-color:var(--accent);font-weight:700}
button.danger{color:#ffb4a9;border-color:#8e3c39}
button:disabled{opacity:.5;cursor:wait}
input[type=file]{display:none}
a{color:var(--accent)}
main{max-width:1600px;margin:0 auto;padding:18px 22px 50px}
.status{padding:10px 13px;border:1px solid var(--line);border-radius:7px;color:var(--muted);margin-bottom:14px}
.tab-nav{display:flex;gap:6px;margin-top:12px;overflow-x:auto}
.tab-button{border:1px solid transparent;border-bottom:0;border-radius:6px 6px 0 0;background:transparent;color:var(--muted);padding:9px 15px;white-space:nowrap}
.tab-button[aria-selected="true"]{background:var(--bg);color:var(--accent);border-color:var(--line);font-weight:700}
.tab-count{display:inline-block;min-width:1.5em;margin-left:4px;padding:0 4px;border-radius:999px;background:var(--line);color:var(--text);font-size:12px;text-align:center}
.panel{min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px}
.panel-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px}
.panel-head h2{margin:0}
iframe{width:100%;border:1px solid var(--line);border-radius:5px;background:#111412}
#candidates{height:80vh;min-height:620px}
#poster{height:80vh;min-height:620px;background:#292d2a}
#posterPlaceholder{display:grid;place-items:center;height:80vh;min-height:620px;color:var(--muted);text-align:center;padding:20px}
.download-link{display:inline-block;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--text);padding:7px 11px;text-decoration:none}
.download-link:hover{color:var(--accent);border-color:var(--accent)}
.layout-choice{display:flex;align-items:center;gap:6px;color:var(--muted);font-size:13px}
.layout-choice select{padding:6px 9px;color:var(--text)}
#jobPanel{margin-bottom:14px}
#jobOutput{max-height:190px;overflow:auto;white-space:pre-wrap;background:#0b0e0c;border:1px solid var(--line);border-radius:6px;padding:10px;font:12px/1.45 ui-monospace,monospace;color:var(--muted)}
.history-list{display:grid;gap:8px}
.history-row{display:grid;grid-template-columns:minmax(170px,1fr) minmax(180px,1fr) auto auto;gap:12px;align-items:center;border-top:1px solid var(--line);padding:10px 2px}
.subscription-row{display:grid;grid-template-columns:64px minmax(170px,1fr) minmax(180px,2fr);gap:12px;align-items:center;border-top:1px solid var(--line);padding:10px 2px}
.subscription-thumbnail,.subscription-thumbnail-placeholder{width:64px;height:64px;border-radius:5px;background:var(--panel)}
.subscription-thumbnail{object-fit:cover}
.subscription-thumbnail-placeholder{display:grid;place-items:center;color:var(--accent);font-size:28px}
.subscription-metadata,.subscription-editor,.subscription-actions{grid-column:1/-1}
.subscription-actions{display:flex;gap:8px}
.subscription-batch input{width:76px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--text);padding:8px;font:inherit}
.subscription-tags{color:var(--accent);font-size:13px}
.subscription-editor{display:grid;gap:8px;padding:10px;background:#111412;border-radius:6px}
.subscription-editor textarea,.subscription-editor input{width:100%;background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:8px;font:inherit}
.subscription-editor textarea{min-height:64px;resize:vertical}
.subscription-editor summary{cursor:pointer;color:var(--accent)}
.subscription-editor label{display:block;color:var(--muted);font-size:13px}
.history-meta{color:var(--muted);font-size:13px}
.badge{display:inline-block;border:1px solid var(--line);border-radius:99px;padding:2px 8px;font-size:12px;white-space:nowrap}
.badge.printed{color:var(--accent)}
.badge.pending{color:var(--orange)}
.badge.unknown{color:var(--muted)}
.notice{color:var(--muted);font-size:13px}
.settings-form{max-width:720px;display:grid;gap:12px}
.settings-form label{display:grid;gap:5px;color:var(--muted);font-size:13px}
.settings-form input:not([type=checkbox]),.settings-form select{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:9px;font:inherit}
.settings-toggle{display:flex!important;align-items:center;gap:9px}
.settings-actions{display:flex;gap:9px;flex-wrap:wrap}
.settings-state{padding:10px;border:1px solid var(--line);border-radius:6px;margin:10px 0}
.settings-debug{margin-top:20px;border-top:1px solid var(--line);padding-top:12px}
.settings-debug summary{cursor:pointer;color:var(--accent)}
.llm-diagnostic-row{border-top:1px solid var(--line);padding:10px 2px}
.llm-diagnostic-row strong{display:block}
[hidden]{display:none!important}
@media(max-width:980px){header{padding:12px 14px 0}.header-row{align-items:flex-start;flex-direction:column}.workspace{grid-template-columns:1fr}#poster,#posterPlaceholder{height:70vh;min-height:440px}.history-row{grid-template-columns:1fr auto;gap:6px}.history-meta{grid-column:1}.subscription-row{grid-template-columns:52px minmax(0,1fr)}.subscription-row>span{grid-column:2}}
@media(max-width:600px){main{padding:14px 12px 32px}.panel-head{align-items:flex-start;flex-direction:column}.history-row{grid-template-columns:1fr}.history-meta{grid-column:auto}}
</style>
</head>
<body>
<header>
  <div class="header-row">
    <h1>Podcast Poster Studio</h1>
    <div class="controls">
      <button class="primary" id="scanButton">Scan subscriptions</button>
    </div>
  </div>
  <nav class="tab-nav" role="tablist" aria-label="Poster workflow">
    <button class="tab-button" id="subscriptionsTab" role="tab" aria-selected="true" aria-controls="subscriptionsPanel" data-tab="subscriptions">0 · Subscriptions</button>
    <button class="tab-button" id="reviewTab" role="tab" aria-selected="false" aria-controls="reviewPanel" data-tab="review">1 · Review episodes <span class="tab-count" id="selectionCount">0</span></button>
    <button class="tab-button" id="selectionTab" role="tab" aria-selected="false" aria-controls="reviewPanel" data-tab="selection" disabled>2 · Edit selection</button>
    <button class="tab-button" id="posterTab" role="tab" aria-selected="false" aria-controls="posterPanel" data-tab="poster">3 · Poster</button>
    <button class="tab-button" id="historyTab" role="tab" aria-selected="false" aria-controls="historyPanel" data-tab="history">4 · History</button>
    <button class="tab-button" id="settingsTab" role="tab" aria-selected="false" aria-controls="settingsPanel" data-tab="settings">5 · Settings</button>
  </nav>
</header>
<main>
  <div class="status" id="status">Starting local app…</div>
  <section id="jobPanel" class="panel" hidden>
    <div class="panel-head"><h2 id="jobTitle">Feed scan</h2><span id="jobState" class="notice"></span></div>
    <pre id="jobOutput"></pre>
  </section>
  <section id="subscriptionsPanel" class="panel tab-panel" role="tabpanel" aria-labelledby="subscriptionsTab">
    <div class="panel-head"><h2>Podcast subscriptions</h2><a id="exportSubscriptions" class="download-link" href="/api/subscriptions/download" hidden>Export OPML</a></div>
    <p class="notice" id="subscriptionsStatus">Your subscriptions are stored locally in user-data. Import a list to start or maintain them.</p>
    <p class="notice">Cached podcast artwork is shown when available. Process subscription sends the RSS description and up to three recent episode titles/descriptions to your configured LLM, then fills the channel metadata editor. Review the suggestions and save them explicitly.</p>
    <div class="controls">
      <label class="upload" for="opmlFile">Choose OPML file</label>
      <input id="opmlFile" type="file" accept=".opml,.xml,application/xml,text/xml">
      <label for="opmlImportMode" class="notice">Import mode</label>
      <select id="opmlImportMode"><option value="merge" selected>Merge (keep existing, add new)</option><option value="replace">Replace current list</option></select>
      <button id="reloadSubscriptions">Refresh list</button>
    </div>
    <div class="controls subscription-batch">
      <label for="subscriptionBatchSize">Batch size</label>
      <input id="subscriptionBatchSize" type="number" min="1" max="25" value="10">
      <span class="notice" id="subscriptionMissingCount">Loading channel metadata status…</span>
      <button class="primary" id="processMissingSubscriptions" disabled>Process subscriptions</button>
    </div>
    <p class="notice" id="subscriptionBatchStatus" aria-live="polite">Missing channel metadata is processed in OPML order; OPML does not record when feeds were added.</p>
    <div id="subscriptionList" class="history-list" aria-live="polite"></div>
  </section>
  <section id="reviewPanel" class="panel tab-panel" role="tabpanel" aria-labelledby="reviewTab" hidden>
    <div class="panel-head"><h2>Review episodes and select up to six</h2><button id="reloadCandidates">Reload list</button></div>
    <iframe id="candidates" title="Podcast episode candidates" src="/candidates"></iframe>
  </section>
  <section id="posterPanel" class="panel tab-panel" role="tabpanel" aria-labelledby="posterTab" hidden>
    <div class="panel-head">
      <h2>Poster preview</h2>
      <div class="controls">
        <label class="layout-choice" for="posterLayout">Layout
          <select id="posterLayout"><option value="list">List poster</option><option value="single">Single episode</option></select>
        </label>
        <label class="layout-choice" for="posterTheme">Theme
          <select id="posterTheme"><option value="dark">Dark</option><option value="ink-saving">White (ink-saving)</option></select>
        </label>
        <a id="printPoster" class="download-link" href="/api/poster" target="_blank" rel="noopener noreferrer" title="Open the PDF in a new tab, then choose Print in your PDF viewer." hidden>Print PDF</a>
        <a id="downloadPoster" class="download-link" href="/api/poster/download" hidden>Download PDF</a>
        <button id="refreshPoster">Refresh preview</button>
        <button class="primary" id="generatePoster">Generate &amp; archive</button>
      </div>
    </div>
    <p class="notice" id="previewHint">Choose episodes in Review, then refresh the preview. Previewing does not add an entry to history.</p>
    <div id="posterPlaceholder">Select episodes in Review, then refresh the preview to see your poster here.</div>
    <iframe id="poster" title="Generated poster PDF" hidden></iframe>
  </section>
  <section id="historyPanel" class="panel tab-panel" role="tabpanel" aria-labelledby="historyTab" hidden>
    <div class="panel-head"><h2>Generated and printed history</h2><div class="controls"><button class="danger" id="clearHistory" disabled>Clear poster archive</button><button id="reloadHistory">Refresh history</button></div></div>
    <p class="notice">Each entry tracks whether its archived poster was marked printed. Force delete removes a printed or older entry and its archived PDF; clearing the poster archive also clears episode warnings. Subscriptions, episode lists, caches, and the current poster are separate.</p>
    <div id="historyList" class="history-list"></div>
  </section>
  <section id="settingsPanel" class="panel tab-panel" role="tabpanel" aria-labelledby="settingsTab" hidden>
    <h2>Optional LLM connection</h2>
    <p class="notice">Disabled by default. Startup only checks common environment-variable names; it never probes an endpoint. The app contacts the configured service only when you explicitly test the connection. This test requests its model list and sends no podcast content.</p>
    <div id="llmPresence" class="settings-state notice" aria-live="polite">Checking for LLM configuration…</div>
    <div class="settings-form">
      <label class="settings-toggle"><input id="llmEnabled" type="checkbox"> Enable LLM connection</label>
      <label for="llmBaseUrl">Base URL<input id="llmBaseUrl" type="url" placeholder="http://127.0.0.1:8080/v1"></label>
      <label for="llmApiFormat">API format<select id="llmApiFormat"><option value="openai-compatible">OpenAI-compatible</option><option value="ollama">Ollama</option></select></label>
      <label for="llmModelChoice">Available models<select id="llmModelChoice"><option value="">Test connection to load model choices</option></select></label>
      <label for="llmModel">Preferred model ID (required; type any ID if it is not listed)<input id="llmModel" type="text" maxlength="200" placeholder="Choose above or enter a model ID"></label>
      <div id="llmCredentialStatus" class="notice">API keys are read from the server environment and are never shown or saved here.</div>
      <div class="settings-actions"><button class="primary" id="saveLlmSettings">Save settings</button><button id="testLlmConnection" disabled>Test connection</button></div>
      <div id="llmTestHint" class="notice" aria-live="polite">Enter a base URL to enable the connection test.</div>
      <div id="llmConnectionStatus" class="notice" aria-live="polite"></div>
    </div>
    <details id="llmDiagnostics" class="settings-debug">
      <summary>Recent LLM diagnostics</summary>
      <p class="notice">The last 50 connection tests and suggestion attempts from this server session. Logs include endpoint host, model, timing, and status only—not episode text, model output, or API keys.</p>
      <button id="refreshLlmDiagnostics" type="button">Refresh diagnostics</button>
      <div id="llmDiagnosticsList" class="history-list" aria-live="polite"></div>
    </details>
  </section>
</main>
<script>
const statusBox = document.getElementById("status");
const scanButton = document.getElementById("scanButton");
const candidatesFrame = document.getElementById("candidates");
const posterFrame = document.getElementById("poster");
const posterPlaceholder = document.getElementById("posterPlaceholder");
const downloadPoster = document.getElementById("downloadPoster");
const printPoster = document.getElementById("printPoster");
const refreshPosterButton = document.getElementById("refreshPoster");
const generatePosterButton = document.getElementById("generatePoster");
const posterLayout = document.getElementById("posterLayout");
const posterTheme = document.getElementById("posterTheme");
const singleLayoutOption = posterLayout.querySelector('option[value="single"]');
const previewHint = document.getElementById("previewHint");
const selectionCount = document.getElementById("selectionCount");
const selectionTab = document.getElementById("selectionTab");
const jobPanel = document.getElementById("jobPanel");
const jobOutput = document.getElementById("jobOutput");
const jobState = document.getElementById("jobState");
const historyList = document.getElementById("historyList");
const clearHistoryButton = document.getElementById("clearHistory");
const subscriptionList = document.getElementById("subscriptionList");
const subscriptionsStatus = document.getElementById("subscriptionsStatus");
const exportSubscriptions = document.getElementById("exportSubscriptions");
const subscriptionBatchSize = document.getElementById("subscriptionBatchSize");
const subscriptionMissingCount = document.getElementById("subscriptionMissingCount");
const processMissingSubscriptionsButton = document.getElementById("processMissingSubscriptions");
const subscriptionBatchStatus = document.getElementById("subscriptionBatchStatus");
const llmEnabled = document.getElementById("llmEnabled");
const llmBaseUrl = document.getElementById("llmBaseUrl");
const llmApiFormat = document.getElementById("llmApiFormat");
const llmModel = document.getElementById("llmModel");
const llmModelChoice = document.getElementById("llmModelChoice");
const llmPresence = document.getElementById("llmPresence");
const llmCredentialStatus = document.getElementById("llmCredentialStatus");
const llmConnectionStatus = document.getElementById("llmConnectionStatus");
const llmTestHint = document.getElementById("llmTestHint");
const llmDiagnostics = document.getElementById("llmDiagnostics");
const llmDiagnosticsList = document.getElementById("llmDiagnosticsList");
const saveLlmSettingsButton = document.getElementById("saveLlmSettings");
const testLlmConnectionButton = document.getElementById("testLlmConnection");
let llmFormInitialized = false;
const panels = {
  subscriptions: document.getElementById("subscriptionsPanel"),
  review: document.getElementById("reviewPanel"),
  poster: document.getElementById("posterPanel"),
  history: document.getElementById("historyPanel"),
  settings: document.getElementById("settingsPanel")
};
let selectedSlots = [];
let hasSavedSlots = false;
let posterSettingsInitialized = false;
let currentSubscriptionFeeds = [];
let processingSubscriptionBatch = false;
const MAX_SUBSCRIPTION_BATCH_SIZE = 25;
let activeTab = "subscriptions";
let candidateHistorySnapshot = null;
let candidateChannelMetadataSnapshot = null;
let candidateLlmSnapshot = null;

function syncCandidateChannelMetadata(feeds){
  candidateChannelMetadataSnapshot = Object.fromEntries(feeds.map(feed => [feed.url, {
    channel_description:feed.channel_description || "",
    tags:Array.isArray(feed.tags) ? feed.tags : []
  }]));
  candidatesFrame.contentWindow?.postMessage({type:"channel-metadata", metadata:candidateChannelMetadataSnapshot}, location.origin);
}

function syncCandidateLlmSettings(settings){
  const hasBaseUrl = Boolean(settings.base_url);
  const hasModel = Boolean(settings.model);
  candidateLlmSnapshot = {
    enabled:settings.enabled === true && hasBaseUrl && hasModel,
    reason:!settings.enabled ? "Enable the LLM connection in Settings." : !hasBaseUrl ? "Set an LLM base URL in Settings." : !hasModel ? "Set a preferred model in Settings." : "",
  };
  candidatesFrame.contentWindow?.postMessage({type:"llm-settings", settings:candidateLlmSnapshot}, location.origin);
}

function syncCandidateHistory(records){
  candidateHistorySnapshot = records;
  const episodes = records.flatMap(record => {
    const printStatus = record.printed_at
      ? "printed"
      : record.printed_at === null && record.has_print_status ? "not_printed" : "unknown";
    return (Array.isArray(record.slots) ? record.slots : []).map(slot => ({
      show:slot.show || "",
      episode:slot.episode || "",
      url:slot.url || "",
      edition:record.edition || record.title || "Earlier poster",
      generated_at:record.generated_at,
      print_status:printStatus
    }));
  });
  candidatesFrame.contentWindow?.postMessage({type:"poster-history", records:episodes}, location.origin);
}

candidatesFrame.addEventListener("load", () => {
  if(candidateLlmSnapshot !== null){
    candidatesFrame.contentWindow?.postMessage({type:"llm-settings", settings:candidateLlmSnapshot}, location.origin);
  }
  if(candidateHistorySnapshot !== null) syncCandidateHistory(candidateHistorySnapshot);
  if(candidateChannelMetadataSnapshot !== null) syncCandidateChannelMetadata(
    Object.entries(candidateChannelMetadataSnapshot).map(([url, value]) => ({url, ...value}))
  );
});

async function requestJson(path, options={}){
  const response = await fetch(path, options);
  const data = await response.json();
  if(!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function renderLlmSettings(settings, force=false){
  if(!settings) return;
  if(force || !llmFormInitialized){
    llmEnabled.checked = settings.enabled === true;
    llmBaseUrl.value = settings.base_url || "http://127.0.0.1:8080/v1";
    llmApiFormat.value = settings.api_format || "openai-compatible";
    llmModel.value = settings.model || "";
    llmFormInitialized = true;
  }
  const sources = [settings.base_url_source, settings.model_source].filter(Boolean);
  const hasConfiguration = Boolean(settings.base_url || settings.model || settings.api_key_available);
  if(hasConfiguration){
    const sourceText = sources.length ? ` Source: ${[...new Set(sources)].join(" and ")}.` : " Environment configuration detected.";
    const stateText = !settings.enabled
      ? " Connection is disabled."
      : !settings.model
        ? " Connection is enabled, but no model is selected. Test connection will choose the first model it finds, or you can enter a model ID manually."
        : " Connection is enabled; use Test connection to verify availability.";
    llmPresence.textContent = `LLM configuration is present.${sourceText}${stateText}`;
  }else{
    llmPresence.textContent = "No LLM endpoint was detected. The suggested local URL is prefilled below, but has not been checked; change it if your service uses another address. No ports are scanned and no service is contacted automatically.";
  }
  llmCredentialStatus.textContent = settings.api_key_available
    ? `An API key is available through ${settings.api_key_env}; its value is hidden and is not saved in config.`
    : "No API key environment variable detected. API keys are never shown or saved in config.";
  syncCandidateLlmSettings(settings);
  updateLlmTestAvailability();
}

function updateLlmTestAvailability(){
  const hasBaseUrl = Boolean(llmBaseUrl.value.trim());
  testLlmConnectionButton.disabled = !llmEnabled.checked || !hasBaseUrl;
  llmTestHint.textContent = !llmEnabled.checked
    ? "Enable the LLM connection and enter a base URL to test it."
    : !hasBaseUrl
      ? "Enter a base URL first (for example, http://127.0.0.1:8080/v1 if that is where your service is running)."
      : "Ready to test. Clicking Test connection saves these settings first.";
}

function llmSettingsPayload(){
  return {
    enabled:llmEnabled.checked,
    base_url:llmBaseUrl.value.trim(),
    api_format:llmApiFormat.value,
    model:llmModel.value.trim()
  };
}

async function saveLlmSettings(){
  const settings = await requestJson("/api/llm/settings", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(llmSettingsPayload())
  });
  renderLlmSettings(settings);
  return settings;
}

async function refreshLlmDiagnostics(){
  llmDiagnosticsList.replaceChildren();
  try{
    const result = await requestJson("/api/llm/diagnostics");
    if(!result.records.length){
      const empty = document.createElement("p");
      empty.className = "notice";
      empty.textContent = "No LLM requests have been made in this server session.";
      llmDiagnosticsList.append(empty);
      return;
    }
    for(const record of result.records){
      const row = document.createElement("div");
      row.className = "llm-diagnostic-row";
      const title = document.createElement("strong");
      title.textContent = `${record.success ? "Success" : "Failure"} · ${record.operation} · ${new Date(record.time).toLocaleString()}`;
      const metadata = document.createElement("div");
      metadata.className = "notice";
      metadata.textContent = `${record.api_format} · ${record.model} · ${record.endpoint} · ${record.duration_ms} ms`;
      const message = document.createElement("div");
      message.textContent = record.message;
      row.append(title, metadata, message);
      llmDiagnosticsList.append(row);
    }
  }catch(error){
    const failure = document.createElement("p");
    failure.className = "notice";
    failure.textContent = `Could not load diagnostics: ${error.message}`;
    llmDiagnosticsList.append(failure);
  }
}

function setActiveTab(name, {autoPreview=true}={}){
  if(name === "selection" && !selectedSlots.length) name = "review";
  activeTab = name;
  for(const button of document.querySelectorAll("[data-tab]")){
    const selected = button.dataset.tab === name;
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
  }
  const visiblePanel = name === "selection" ? "review" : name;
  for(const [panelName, panel] of Object.entries(panels)) panel.hidden = panelName !== visiblePanel;
  if(name === "selection"){
    candidatesFrame.contentWindow.postMessage({type:"open-selection-review"}, location.origin);
  } else if(name === "review"){
    candidatesFrame.contentWindow.postMessage({type:"close-selection-review"}, location.origin);
  }
  if(name === "history") refreshHistory().catch(error => { statusBox.textContent = error.message; });
  if(name === "subscriptions") refreshSubscriptions().catch(error => { statusBox.textContent = error.message; });
  if(name === "settings") refreshStatus().catch(error => { statusBox.textContent = error.message; });
  if(name === "poster" && autoPreview) refreshPreview();
}

for(const button of document.querySelectorAll("[data-tab]")){
  button.addEventListener("click", () => setActiveTab(button.dataset.tab));
}

function updateSelection(slots){
  selectedSlots = Array.isArray(slots) ? slots : [];
  selectionCount.textContent = String(selectedSlots.length);
  selectionTab.disabled = selectedSlots.length === 0;
  if(!selectedSlots.length && activeTab === "selection") setActiveTab("review");
  singleLayoutOption.disabled = selectedSlots.length !== 1;
  if(singleLayoutOption.disabled && posterLayout.value === "single") posterLayout.value = "list";
  generatePosterButton.disabled = selectedSlots.length === 0 && !hasSavedSlots;
  previewHint.textContent = selectedSlots.length
    ? `Preview updates when you open Poster. Your ${selectedSlots.length} selected episode${selectedSlots.length === 1 ? "" : "s"} will be used; edit summaries in Edit selection.`
    : "Choose episodes in Review, then open Poster to refresh the preview. Previewing does not add an entry to history.";
}

async function refreshStatus({reloadCandidates=false}={}){
  const data = await requestJson("/api/status");
  renderLlmSettings(data.llm);
  if(!posterSettingsInitialized){
    posterLayout.value = data.poster_layout || "list";
    posterTheme.value = data.poster_theme || "dark";
    posterSettingsInitialized = true;
  }
  statusBox.textContent = data.opml_exists
    ? `Subscriptions: ${data.opml_name} · Poster cadence: ${data.poster_period} · Saved layout: ${data.poster_layout} · Theme: ${data.poster_theme || "dark"} · Local data stays on this computer.`
    : "No OPML subscriptions found. Import your AntennaPod OPML file to begin.";
  hasSavedSlots = data.has_slots;
  generatePosterButton.disabled = selectedSlots.length === 0 && !hasSavedSlots;
  if(data.poster_ready){
    posterPlaceholder.hidden = true;
    posterFrame.hidden = false;
    downloadPoster.hidden = false;
    printPoster.hidden = false;
    posterFrame.src = `/api/poster?refresh=${Date.now()}`;
  } else {
    posterFrame.hidden = true;
    posterPlaceholder.hidden = false;
    downloadPoster.hidden = true;
    printPoster.hidden = true;
  }
  if(reloadCandidates && data.candidates_ready){
    candidatesFrame.src = `/candidates?refresh=${Date.now()}`;
    updateSelection([]);
  }
}

function subscriptionNeedsMetadata(feed){
  return !String(feed.channel_description || "").trim() || !Array.isArray(feed.tags) || feed.tags.length === 0;
}

function updateSubscriptionBatchControls(){
  const missingCount = currentSubscriptionFeeds.filter(subscriptionNeedsMetadata).length;
  const maximum = Math.min(MAX_SUBSCRIPTION_BATCH_SIZE, missingCount);
  subscriptionMissingCount.textContent = missingCount
    ? `${missingCount} subscription${missingCount === 1 ? "" : "s"} missing a channel description or default tags.`
    : "All subscriptions have channel descriptions and default tags.";
  subscriptionBatchSize.max = String(Math.max(1, maximum));
  let requested = Number.parseInt(subscriptionBatchSize.value, 10);
  if(!Number.isFinite(requested) || requested < 1) requested = Math.min(10, Math.max(1, maximum));
  requested = Math.min(requested, Math.max(1, maximum));
  subscriptionBatchSize.value = String(requested);
  processMissingSubscriptionsButton.textContent = missingCount
    ? `Process first ${Math.min(requested, missingCount)} of ${missingCount} missing`
    : "All metadata processed";
  processMissingSubscriptionsButton.disabled = missingCount === 0 || processingSubscriptionBatch;
  subscriptionBatchSize.disabled = processingSubscriptionBatch || missingCount === 0;
}

async function processMissingSubscriptions(){
  if(processingSubscriptionBatch) return;
  const pending = currentSubscriptionFeeds.filter(subscriptionNeedsMetadata);
  if(!pending.length){
    updateSubscriptionBatchControls();
    return;
  }
  const batchSize = Math.max(1, Math.min(
    MAX_SUBSCRIPTION_BATCH_SIZE,
    pending.length,
    Number.parseInt(subscriptionBatchSize.value, 10) || 10
  ));
  const batch = pending.slice(0, batchSize);

  try{
    const status = await requestJson("/api/status");
    if(!status.llm?.enabled || !status.llm.base_url || !status.llm.model){
      statusBox.textContent = "Enable the LLM, configure its base URL, and select a model in Settings before processing channel metadata.";
      return;
    }
  }catch(error){
    statusBox.textContent = `Could not check LLM settings: ${error.message}`;
    return;
  }

  processingSubscriptionBatch = true;
  updateSubscriptionBatchControls();
  let savedCount = 0;
  const failures = [];
  try{
    for(let index = 0; index < batch.length; index++){
      const feed = batch[index];
      const progress = `${index + 1} of ${batch.length}`;
      subscriptionBatchStatus.textContent = `Processing ${progress}: ${feed.title}…`;
      statusBox.textContent = `Processing channel metadata ${progress}: ${feed.title}…`;
      try{
        const suggestion = await requestJson("/api/llm/channel-suggest", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({feed_url:feed.url})
        });
        await requestJson("/api/subscriptions/metadata", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({
            feed_url:feed.url,
            channel_description:String(feed.channel_description || "").trim() || suggestion.channel_description,
            tags:Array.isArray(feed.tags) && feed.tags.length ? feed.tags : suggestion.tags
          })
        });
        savedCount++;
      }catch(error){
        failures.push(`${feed.title}: ${error.message}`);
      }
      subscriptionBatchStatus.textContent = `Processed ${progress}; saved ${savedCount}${failures.length ? `, failed ${failures.length}` : ""}.`;
    }
    await refreshSubscriptions();
    const failureDetails = failures.length ? ` Failures: ${failures.slice(0, 3).join("; ")}${failures.length > 3 ? "; …" : ""}` : "";
    statusBox.textContent = `Channel metadata processing finished: saved ${savedCount} of ${batch.length}.${failureDetails}`;
    subscriptionBatchStatus.textContent = `Finished ${batch.length} requested; saved ${savedCount}, failed ${failures.length}.`;
  }catch(error){
    statusBox.textContent = `Channel metadata processing stopped: ${error.message}`;
    subscriptionBatchStatus.textContent = "Could not refresh the subscription list after processing.";
  }finally{
    processingSubscriptionBatch = false;
    updateSubscriptionBatchControls();
  }
}

async function refreshSubscriptions(){
  const data = await requestJson("/api/subscriptions");
  currentSubscriptionFeeds = Array.isArray(data.feeds) ? data.feeds : [];
  updateSubscriptionBatchControls();
  syncCandidateChannelMetadata(currentSubscriptionFeeds);
  subscriptionList.replaceChildren();
  exportSubscriptions.hidden = !data.exists;
  subscriptionsStatus.textContent = data.exists
    ? `${data.feeds.length} subscriptions in ${data.opml}. Import another OPML file to merge or replace this list.`
    : "No subscriptions yet. Import an OPML list to get started.";
  if(!data.feeds.length){
    const empty = document.createElement("p");
    empty.className = "notice";
    empty.textContent = "No podcast feeds found.";
    subscriptionList.append(empty);
    return;
  }
  for(const feed of data.feeds){
    const row = document.createElement("div");
    row.className = "subscription-row";
    const thumbnail = document.createElement(feed.artwork_url ? "img" : "div");
    thumbnail.className = feed.artwork_url ? "subscription-thumbnail" : "subscription-thumbnail-placeholder";
    if(feed.artwork_url){
      thumbnail.src = feed.artwork_url;
      thumbnail.alt = `Podcast artwork for ${feed.title}`;
      thumbnail.loading = "lazy";
      thumbnail.decoding = "async";
    }else{
      thumbnail.setAttribute("aria-hidden", "true");
      thumbnail.textContent = "♫";
    }
    const title = document.createElement("strong");
    title.textContent = feed.groups.length ? `${feed.groups.join(" / ")} · ${feed.title}` : feed.title;
    const url = document.createElement("span");
    url.className = "notice";
    url.textContent = feed.url;
    row.append(thumbnail, title, url);
    const metadata = document.createElement("div");
    metadata.className = "subscription-metadata";
    metadata.textContent = feed.channel_description || "No channel description / editorial note yet.";
    if(feed.tags.length){
      const tagLine = document.createElement("div");
      tagLine.className = "subscription-tags";
      tagLine.textContent = feed.tags.map(tag => `#${tag}`).join(" ");
      metadata.append(tagLine);
    }
    row.append(metadata);

    const editor = document.createElement("details");
    editor.className = "subscription-editor";
    const editorSummary = document.createElement("summary");
    editorSummary.textContent = "Edit channel description and tags";
    const descriptionLabel = document.createElement("label");
    descriptionLabel.textContent = "Channel description / editorial note (up to 400 characters)";
    const description = document.createElement("textarea");
    description.maxLength = 400;
    description.value = feed.channel_description || "";
    descriptionLabel.append(description);
    const tagsLabel = document.createElement("label");
    tagsLabel.textContent = "Default tags (comma-separated; episodes inherit these)";
    const tagsInput = document.createElement("input");
    tagsInput.type = "text";
    tagsInput.maxLength = 500;
    tagsInput.placeholder = "Environment, Greens affiliated";
    tagsInput.value = feed.tags.join(", ");
    tagsLabel.append(tagsInput);
    const subscriptionActions = document.createElement("div");
    subscriptionActions.className = "subscription-actions";
    const suggestMetadata = document.createElement("button");
    suggestMetadata.textContent = "Process subscription";
    suggestMetadata.title = "Use the configured LLM to suggest this channel's description and default tags";
    suggestMetadata.addEventListener("click", async () => {
      editor.open = true;
      suggestMetadata.disabled = true;
      statusBox.textContent = `Generating channel metadata suggestions for ${feed.title}…`;
      try{
        const suggestion = await requestJson("/api/llm/channel-suggest", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({feed_url:feed.url})
        });
        description.value = suggestion.channel_description;
        tagsInput.value = suggestion.tags.join(", ");
        statusBox.textContent = `Suggested channel description and tags for ${feed.title}. Review them, then save if they look right.`;
      }catch(error){ statusBox.textContent = `Could not suggest channel metadata: ${error.message}`; }
      finally{ suggestMetadata.disabled = false; }
    });
    const saveMetadata = document.createElement("button");
    saveMetadata.className = "primary";
    saveMetadata.textContent = "Save channel metadata";
    saveMetadata.addEventListener("click", async () => {
      saveMetadata.disabled = true;
      try{
        await requestJson("/api/subscriptions/metadata", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({
            feed_url:feed.url,
            channel_description:description.value,
            tags:tagsInput.value.split(",").map(tag => tag.trim()).filter(Boolean)
          })
        });
        statusBox.textContent = `Saved channel metadata for ${feed.title}.`;
        await refreshSubscriptions();
      }catch(error){ statusBox.textContent = `Could not save channel metadata: ${error.message}`; }
      finally{ saveMetadata.disabled = false; }
    });
    editor.append(editorSummary, descriptionLabel, tagsLabel, saveMetadata);
    subscriptionActions.append(suggestMetadata);
    row.append(subscriptionActions, editor);
    subscriptionList.append(row);
  }
}

async function refreshHistory(){
  const records = await requestJson("/api/history");
  syncCandidateHistory(records);
  historyList.replaceChildren();
  clearHistoryButton.disabled = records.length === 0;
  if(!records.length){
    const empty = document.createElement("p");
    empty.className = "notice";
    empty.textContent = "No posters have been generated yet.";
    historyList.append(empty);
    return;
  }
  for(const record of records){
    const row = document.createElement("div");
    row.className = "history-row";
    const title = document.createElement("strong");
    const layout = record.layout === "single" ? "Single episode" : "List";
    title.textContent = `${layout} · ${record.edition || record.title || "Poster"}`;
    const generated = document.createElement("span");
    generated.className = "history-meta";
    generated.textContent = `Generated ${new Date(record.generated_at).toLocaleString()}`;
    const state = document.createElement("span");
    const status = record.printed_at ? "printed" : (record.printed_at === null && record.has_print_status ? "pending" : "unknown");
    state.className = `badge ${status}`;
    state.textContent = status === "printed" ? `Printed ${new Date(record.printed_at).toLocaleDateString()}` : status === "pending" ? "Not marked printed" : "Print status unknown";
    const actions = document.createElement("div");
    actions.className = "controls";
    const printPdf = document.createElement("a");
    printPdf.href = `/api/history/${encodeURIComponent(record.manifest)}/pdf`;
    printPdf.target = "_blank";
    printPdf.rel = "noopener noreferrer";
    printPdf.className = "download-link";
    printPdf.title = "Open the PDF in a new tab, then choose Print in your PDF viewer.";
    printPdf.textContent = "Print PDF";
    const download = document.createElement("a");
    download.href = `/api/history/${encodeURIComponent(record.manifest)}/download`;
    download.className = "download-link";
    download.textContent = "Download PDF";
    const toggle = document.createElement("button");
    toggle.textContent = record.printed_at ? "Mark not printed" : "Mark printed";
    toggle.addEventListener("click", async () => {
      try{
        await requestJson("/api/history/printed", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({manifest:record.manifest, printed:!record.printed_at})
        });
        await refreshHistory();
      }catch(error){ statusBox.textContent = error.message; }
    });
    actions.append(printPdf, download, toggle);
    const remove = document.createElement("button");
    remove.className = status === "pending" ? "" : "danger";
    remove.textContent = status === "pending" ? "Delete unprinted" : "Force delete";
    remove.addEventListener("click", async () => {
      const force = status !== "pending";
      const prompt = force
        ? `Force-delete ${record.edition || record.title || "this poster"}? This permanently removes its archived PDF and stops using it for episode warnings.`
        : "Permanently delete this unprinted PDF and its history entry? It will no longer be used to warn about previously posted episodes.";
      if(!window.confirm(prompt)) return;
      try{
        await requestJson(force ? "/api/history/force-delete" : "/api/history/delete", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({manifest:record.manifest, ...(force ? {confirm:true} : {})})
        });
        statusBox.textContent = force ? "Poster force-deleted from history." : "Unprinted poster removed from history.";
        await refreshHistory();
      }catch(error){ statusBox.textContent = error.message; }
    });
    actions.append(remove);
    row.append(title, generated, state, actions);
    historyList.append(row);
  }
}

async function refreshPreview(){
  refreshPosterButton.disabled = true;
  try{
    if(selectedSlots.length){
      statusBox.textContent = `Building a preview from ${selectedSlots.length} selected episode${selectedSlots.length === 1 ? "" : "s"}…`;
      await requestJson("/api/preview", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({slots:selectedSlots, layout:posterLayout.value, theme:posterTheme.value})
      });
      await refreshStatus();
      statusBox.textContent = "Preview refreshed from your current selection. It has not been added to history.";
    } else if(posterFrame.hidden){
      statusBox.textContent = "Select episodes in Review before refreshing the preview.";
    } else {
      await refreshStatus();
      statusBox.textContent = "Preview refreshed from the current PDF.";
    }
  }catch(error){
    statusBox.textContent = `Could not refresh preview: ${error.message}`;
  }finally{
    refreshPosterButton.disabled = false;
  }
}

async function runGeneration(path, body){
  generatePosterButton.disabled = true;
  refreshPosterButton.disabled = true;
  scanButton.disabled = true;
  statusBox.textContent = "Generating the PDF and archiving this selection…";
  try{
    await requestJson(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body || {})});
    await refreshStatus();
    await refreshHistory();
    setActiveTab("poster", {autoPreview:false});
    statusBox.textContent = "Poster generated and archived. Mark it printed in history after printing or posting it.";
  }catch(error){
    statusBox.textContent = `Poster generation failed: ${error.message}`;
  }finally{
    scanButton.disabled = false;
    refreshPosterButton.disabled = false;
    generatePosterButton.disabled = selectedSlots.length === 0 && !hasSavedSlots;
  }
}

async function pollJob(jobId){
  jobPanel.hidden = false;
  document.getElementById("jobTitle").textContent = "Scanning subscriptions";
  while(true){
    const job = await requestJson(`/api/jobs/${jobId}`);
    jobState.textContent = job.status;
    jobOutput.textContent = job.output.join("\n");
    jobOutput.scrollTop = jobOutput.scrollHeight;
    if(job.status === "complete"){
      statusBox.textContent = "Feed scan complete. Review the refreshed episode list below.";
      await refreshStatus({reloadCandidates:true});
      setActiveTab("review");
      jobPanel.hidden = false;
      return;
    }
    if(job.status === "failed"){
      statusBox.textContent = "Feed scan failed. See the scan log above.";
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
}

scanButton.addEventListener("click", async () => {
  scanButton.disabled = true;
  statusBox.textContent = "Starting feed scan…";
  try{
    const job = await requestJson("/api/scan", {method:"POST"});
    await pollJob(job.job_id);
  }catch(error){
    statusBox.textContent = `Could not scan feeds: ${error.message}`;
  }finally{
    scanButton.disabled = false;
  }
});

generatePosterButton.addEventListener("click", () => {
  if(selectedSlots.length){
    runGeneration("/api/generate", {slots:selectedSlots, layout:posterLayout.value, theme:posterTheme.value});
  } else {
    runGeneration("/api/generate-current", {layout:posterLayout.value, theme:posterTheme.value});
  }
});
refreshPosterButton.addEventListener("click", refreshPreview);
posterLayout.addEventListener("change", () => {
  if(activeTab === "poster") refreshPreview();
});
posterTheme.addEventListener("change", () => {
  if(activeTab === "poster") refreshPreview();
});
document.getElementById("reloadCandidates").addEventListener("click", () => {
  setActiveTab("review");
  updateSelection([]);
  candidatesFrame.src = `/candidates?refresh=${Date.now()}`;
});
document.getElementById("reloadHistory").addEventListener("click", refreshHistory);
clearHistoryButton.addEventListener("click", async () => {
  if(!window.confirm("Permanently delete all archived poster PDFs and their printed/unprinted history records? This clears old-episode warnings. It does not delete subscriptions, episode lists, caches, or the current poster PDF.")) return;
  try{
    const result = await requestJson("/api/history/clear", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({confirm:true})
    });
    statusBox.textContent = `Cleared ${result.entries} archived poster records and ${result.pdfs} PDFs.`;
    await refreshHistory();
  }catch(error){ statusBox.textContent = error.message; }
});
document.getElementById("reloadSubscriptions").addEventListener("click", () => {
  refreshSubscriptions().catch(error => { statusBox.textContent = error.message; });
});
subscriptionBatchSize.addEventListener("input", updateSubscriptionBatchControls);
processMissingSubscriptionsButton.addEventListener("click", processMissingSubscriptions);
document.getElementById("refreshLlmDiagnostics").addEventListener("click", refreshLlmDiagnostics);
llmDiagnostics.addEventListener("toggle", () => {
  if(llmDiagnostics.open) refreshLlmDiagnostics();
});
llmEnabled.addEventListener("change", updateLlmTestAvailability);
llmBaseUrl.addEventListener("input", updateLlmTestAvailability);
llmModelChoice.addEventListener("change", () => {
  if(llmModelChoice.value) llmModel.value = llmModelChoice.value;
});
llmModel.addEventListener("input", () => {
  llmModelChoice.value = [...llmModelChoice.options].some(option => option.value === llmModel.value.trim())
    ? llmModel.value.trim()
    : "";
});
saveLlmSettingsButton.addEventListener("click", async () => {
  saveLlmSettingsButton.disabled = true;
  llmConnectionStatus.textContent = "Saving LLM settings…";
  try{
    const settings = await saveLlmSettings();
    llmConnectionStatus.textContent = settings.enabled
      ? "Settings saved. No LLM request has been made; use Test connection when ready."
      : "Settings saved. LLM connection remains disabled.";
  }catch(error){ llmConnectionStatus.textContent = `Could not save LLM settings: ${error.message}`; }
  finally{ saveLlmSettingsButton.disabled = false; }
});
testLlmConnectionButton.addEventListener("click", async () => {
  testLlmConnectionButton.disabled = true;
  saveLlmSettingsButton.disabled = true;
  llmConnectionStatus.textContent = "Saving settings and requesting the service's model list…";
  try{
    await saveLlmSettings();
    const result = await requestJson("/api/llm/test", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({test:true})
    });
    const modelPlaceholder = document.createElement("option");
    modelPlaceholder.value = "";
    modelPlaceholder.textContent = result.models.length ? "Choose a model…" : "No models returned; enter an ID below";
    llmModelChoice.replaceChildren(modelPlaceholder, ...result.models.map(model => {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      return option;
    }));
    llmModelChoice.value = result.models.includes(llmModel.value.trim()) ? llmModel.value.trim() : "";
    let modelHint = "";
    if(!llmModel.value.trim() && result.models.length === 1){
      llmModel.value = result.models[0];
      llmModelChoice.value = result.models[0];
      await saveLlmSettings();
      modelHint = ` Selected and saved the only available model, ${result.models[0]}.`;
    }else if(!llmModel.value.trim() && result.models.length > 1){
      modelHint = " Choose an available model above or type an ID, then save settings to enable suggestions.";
    }else if(!llmModel.value.trim()){
      modelHint = " No model IDs were returned; enter the model ID manually and save settings to enable suggestions.";
    }
    const models = result.models.length ? ` Models: ${result.models.join(", ")}.` : " The service returned no model names.";
    llmConnectionStatus.textContent = `Connection succeeded (${result.api_format}).${models}${modelHint}`;
  }catch(error){ llmConnectionStatus.textContent = `Connection test failed: ${error.message}`; }
  finally{
    saveLlmSettingsButton.disabled = false;
    updateLlmTestAvailability();
  }
});
document.getElementById("opmlFile").addEventListener("change", async event => {
  const file = event.target.files[0];
  if(!file) return;
  const mode = document.getElementById("opmlImportMode").value;
  if(mode === "replace" && !window.confirm("Replace your current subscription list with this OPML file?")){
    event.target.value = "";
    return;
  }
  statusBox.textContent = `${mode === "merge" ? "Merging" : "Replacing subscriptions with"} ${file.name}…`;
  try{
    const result = await requestJson(`/api/subscriptions?mode=${mode}`, {method:"POST", headers:{"Content-Type":"application/xml"}, body:await file.arrayBuffer()});
    statusBox.textContent = `${mode === "merge" ? `Added ${result.added} new` : "Imported"} subscriptions; ${result.feeds} total in ${result.opml}. Scan subscriptions to refresh episodes.`;
    await Promise.all([refreshSubscriptions(), refreshStatus()]);
  }catch(error){ statusBox.textContent = `Could not import OPML: ${error.message}`; }
  event.target.value = "";
});

window.addEventListener("message", event => {
  if(event.origin !== location.origin || event.source !== candidatesFrame.contentWindow) return;
  if(event.data?.type === "candidate-selection"){
    updateSelection(event.data.slots);
    return;
  }
  if(event.data?.type === "show-episodes-tab"){
    setActiveTab("review");
    return;
  }
  if(event.data?.type === "poster-generated"){
    refreshStatus().then(refreshHistory);
    setActiveTab("poster", {autoPreview:false});
    statusBox.textContent = "Poster generated and archived. Mark it printed in history after printing or posting it.";
  }
});

Promise.all([refreshStatus({reloadCandidates:true}), refreshHistory(), refreshSubscriptions()]).catch(error => { statusBox.textContent = error.message; });
</script>
</body>
</html>'''

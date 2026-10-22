APP_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Podcast Poster Studio</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%23111412'/%3E%3Cpath d='M9 22V10l14 6z' fill='%234fd1c5'/%3E%3C/svg%3E">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<style>
:root{color-scheme:dark;--bg:#111412;--panel:#1a1f1c;--panel-2:#151a17;--line:#303a34;--muted:#9ba79f;--text:#edf2ee;--accent:#4fd1c5;--orange:#f0ad63;--danger:#ffb4a9}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}
header{position:sticky;top:0;z-index:5;background:#171c19;border-bottom:1px solid var(--line)}
.header-row{max-width:1600px;margin:0 auto;display:flex;align-items:center;gap:18px;padding:10px 22px}
.brand{font-weight:800;font-size:18px;color:var(--text);text-decoration:none;white-space:nowrap}
h2{font-size:18px;margin:0}
h3{font-size:16px;margin:0 0 6px}
.tab-nav{display:flex;align-items:center;gap:4px;flex:1;min-width:0;overflow-x:auto;padding:2px}
.tab-button{border:1px solid transparent;border-radius:999px;background:transparent;color:var(--muted);padding:6px 13px;white-space:nowrap;font:inherit;cursor:pointer;display:inline-flex;align-items:center;gap:7px}
.tab-button:hover{color:var(--text)}
.tab-button[aria-selected="true"]{background:rgba(79,209,197,.12);color:var(--accent);border-color:var(--accent);font-weight:700}
.step-number{display:inline-grid;place-items:center;width:20px;height:20px;border-radius:50%;border:1px solid currentColor;font-size:12px;font-weight:700}
.step-arrow{color:#56635b}
.nav-spacer{flex:1;min-width:12px}
.tab-count{display:inline-block;min-width:2.4em;padding:0 6px;border-radius:999px;background:var(--line);color:var(--text);font-size:12px;text-align:center}
.tab-count.full{background:var(--accent);color:#10201d}
main{max-width:1600px;margin:0 auto;padding:18px 22px 60px}
body.has-tray main{padding-bottom:110px}
.panel{min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px}
.panel-head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;margin-bottom:12px;flex-wrap:wrap}
.panel-head p{margin:3px 0 0}
.controls{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
button,.upload,select{border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--text);padding:8px 12px;font:inherit;cursor:pointer}
button:hover:not(:disabled),.upload:hover{border-color:var(--accent)}
button.primary{background:var(--accent);color:#10201d;border-color:var(--accent);font-weight:700}
button.danger{color:var(--danger);border-color:#8e3c39}
button.link-button{background:none;border:0;color:var(--accent);padding:0;text-decoration:underline;font:inherit}
button:disabled{opacity:.5;cursor:not-allowed}
input[type=file]{display:none}
a{color:var(--accent)}
.notice{color:var(--muted);font-size:13px}
.download-link{display:inline-block;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--text);padding:7px 11px;text-decoration:none}
.download-link:hover{color:var(--accent);border-color:var(--accent)}
.empty-state{border:1px dashed var(--line);border-radius:8px;padding:36px 20px;text-align:center;color:var(--muted)}
.empty-state h3{color:var(--text)}
.empty-state p{margin:0 auto;max-width:560px}
.empty-state .controls{justify-content:center;margin-top:16px}
.job-panel{margin-bottom:14px}
.job-panel.failed{border-color:#8e3c39}
.job-panel .panel-head{margin-bottom:6px;align-items:center}
.job-panel details summary{cursor:pointer;color:var(--accent);font-size:13px}
#jobOutput{max-height:190px;overflow:auto;white-space:pre-wrap;background:#0b0e0c;border:1px solid var(--line);border-radius:6px;padding:10px;font:12px/1.45 ui-monospace,monospace;color:var(--muted)}
#candidates{display:block;width:100%;height:640px;border:0;background:transparent}
.tray{position:fixed;left:0;right:0;bottom:0;z-index:4;background:#1a201d;border-top:1px solid var(--line);box-shadow:0 -8px 24px #0006}
.tray-inner{max-width:1600px;margin:0 auto;padding:10px 22px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}
.tray-summary{display:flex;align-items:center;gap:14px;min-width:0}
.tray-thumbs{display:flex;gap:4px}
.tray-thumbs img,.tray-thumbs span{width:34px;height:34px;border-radius:5px;object-fit:cover;background:var(--panel);display:grid;place-items:center;color:var(--accent)}
.tray-thumbs .tray-slot-empty{border:1px dashed #4a5750;background:transparent}
.toasts{position:fixed;right:18px;bottom:90px;z-index:10;display:grid;gap:8px;width:min(420px,calc(100vw - 36px))}
.toast{background:#223029;border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:7px;padding:10px 12px;display:flex;gap:10px;align-items:flex-start;box-shadow:0 8px 24px #0008}
.toast.error{border-left-color:#e0685e}
.toast>div{flex:1}
.toast button{padding:3px 10px}
.toast .toast-close{border:0;background:none;color:var(--muted);font-size:18px;line-height:1;padding:0 2px}
.edit-list{display:grid;gap:12px}
.edit-card{display:grid;grid-template-columns:84px minmax(0,1fr);gap:16px;border:1px solid var(--line);border-radius:8px;padding:14px;background:var(--panel-2)}
.edit-art{width:84px;height:84px;border-radius:6px;object-fit:cover;background:var(--panel);display:grid;place-items:center;color:var(--accent);font-size:30px}
.edit-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.edit-show{color:var(--accent);font-weight:700}
.edit-title{font-weight:600;font-size:16px}
.edit-title a{color:var(--text);text-decoration:none}
.edit-title a:hover{color:var(--accent);text-decoration:underline}
.edit-meta{color:var(--muted);font-size:13px}
.posted-note{color:var(--orange);font-size:12px;margin-top:2px}
.edit-order{display:flex;gap:6px;flex-shrink:0}
.edit-order button{padding:4px 10px}
.field{display:grid;gap:5px;margin-top:12px;color:var(--muted);font-size:13px}
.field textarea,.field input{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:9px;font:inherit}
.field textarea{min-height:86px;resize:vertical}
.field-foot{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap;margin-top:6px}
.field-tools{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.field-tools button{padding:4px 10px;font-size:13px}
.char-count{font-size:12px;color:var(--muted)}
.char-count.near{color:var(--orange)}
.feedback{font-size:13px;color:var(--muted);margin-top:4px}
.save-state{font-size:13px;color:var(--muted);padding-top:4px}
.save-state.error{color:var(--danger)}
.banner{border:1px solid var(--accent);background:rgba(79,209,197,.08);border-radius:8px;padding:12px 14px;margin-bottom:12px;display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap}
.layout-choice{display:flex;align-items:center;gap:6px;color:var(--muted);font-size:13px}
.layout-choice select{padding:6px 9px;color:var(--text)}
.preview-wrap{position:relative;min-height:560px}
#poster{display:block;width:100%;height:80vh;min-height:560px;border:1px solid var(--line);border-radius:5px;background:#292d2a}
.preview-overlay{position:absolute;inset:0;display:grid;place-items:center;align-content:center;gap:12px;background:rgba(17,20,18,.85);border-radius:5px;text-align:center;padding:20px}
.history-list{display:grid;gap:8px}
.history-row{display:grid;grid-template-columns:minmax(170px,1fr) minmax(180px,1fr) auto auto;gap:12px;align-items:center;border-top:1px solid var(--line);padding:10px 2px}
.history-meta{color:var(--muted);font-size:13px}
.history-preview{grid-column:1/-1}
.history-preview iframe{width:100%;height:60vh;min-height:420px;border:1px solid var(--line);border-radius:8px;margin-top:8px}
.history-locations{grid-column:1/-1;margin-top:8px}
.location-map{height:280px;border:1px solid var(--line);border-radius:8px}
.location-list{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.location-item{display:flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:999px;padding:4px 6px 4px 12px;font-size:13px}
.location-item button{padding:2px 8px;font-size:12px}
.location-known{margin-top:10px;border-top:1px solid var(--line);padding-top:10px}
.location-known button{font-size:13px}
.subscription-row{display:grid;grid-template-columns:64px minmax(170px,1fr) minmax(180px,2fr);gap:12px;align-items:center;border-top:1px solid var(--line);padding:10px 2px}
.subscription-thumbnail,.subscription-thumbnail-placeholder{width:64px;height:64px;border-radius:5px;background:var(--panel)}
.subscription-thumbnail{object-fit:cover}
.subscription-thumbnail-placeholder{display:grid;place-items:center;color:var(--accent);font-size:28px}
.subscription-metadata,.subscription-editor{grid-column:1/-1}
.subscription-batch{margin:8px 0}
.subscription-batch input{width:76px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--text);padding:8px;font:inherit}
.subscription-tags{color:var(--accent);font-size:13px}
.subscription-editor{display:grid;gap:8px;padding:10px;background:#111412;border-radius:6px}
.subscription-editor textarea,.subscription-editor input{width:100%;background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:8px;font:inherit}
.subscription-editor textarea{min-height:64px;resize:vertical}
.subscription-editor summary{cursor:pointer;color:var(--accent)}
.subscription-editor label{display:block;color:var(--muted);font-size:13px}
.badge{display:inline-block;border:1px solid var(--line);border-radius:99px;padding:2px 8px;font-size:12px;white-space:nowrap}
.badge.printed{color:var(--accent)}
.badge.pending{color:var(--orange)}
.badge.unknown{color:var(--muted)}
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
@media(max-width:980px){.header-row{flex-wrap:wrap;padding:10px 14px;gap:8px}.tab-nav{flex-basis:100%}main{padding:14px 12px 60px}.history-row{grid-template-columns:1fr auto;gap:6px}.history-meta{grid-column:1}.subscription-row{grid-template-columns:52px minmax(0,1fr)}.subscription-row>span{grid-column:2}#poster{height:70vh;min-height:440px}.tray-inner{padding:10px 12px}}
@media(max-width:640px){.panel-head{flex-direction:column}.job-panel .panel-head{flex-direction:row}.edit-card{grid-template-columns:1fr}.edit-art{width:64px;height:64px}.history-row{grid-template-columns:1fr}.history-meta{grid-column:auto}.tab-nav{flex-wrap:wrap;overflow:visible}.tab-button{padding:5px 10px}.step-arrow{display:none}.nav-spacer{flex-basis:100%;height:0}.tray-hint,.tray-thumbs{display:none}.toast:nth-last-child(n+3){display:none}}
</style>
</head>
<body>
<header>
  <div class="header-row">
    <a class="brand" href="#pick">Podcast Poster Studio</a>
    <nav class="tab-nav" role="tablist" aria-label="Poster studio">
      <button class="tab-button" id="pickTab" role="tab" aria-selected="false" aria-controls="pickPanel" data-tab="pick"><span class="step-number">1</span>Pick episodes <span class="tab-count" id="selectionCount">0/6</span></button>
      <span class="step-arrow" aria-hidden="true">›</span>
      <button class="tab-button" id="editTab" role="tab" aria-selected="false" aria-controls="editPanel" data-tab="edit"><span class="step-number">2</span>Edit text</button>
      <span class="step-arrow" aria-hidden="true">›</span>
      <button class="tab-button" id="posterTab" role="tab" aria-selected="false" aria-controls="posterPanel" data-tab="poster"><span class="step-number">3</span>Poster</button>
      <span class="nav-spacer"></span>
      <button class="tab-button" id="subscriptionsTab" role="tab" aria-selected="false" aria-controls="subscriptionsPanel" data-tab="subscriptions">Subscriptions</button>
      <button class="tab-button" id="historyTab" role="tab" aria-selected="false" aria-controls="historyPanel" data-tab="history">History</button>
      <button class="tab-button" id="settingsTab" role="tab" aria-selected="false" aria-controls="settingsPanel" data-tab="settings">Settings</button>
    </nav>
  </div>
</header>
<main>
  <section id="jobPanel" class="panel job-panel" hidden aria-live="polite">
    <div class="panel-head"><div><h2 id="jobTitle">Scanning your feeds…</h2><div id="jobState" class="notice"></div></div><button id="hideJob" type="button">Hide</button></div>
    <details id="jobLog"><summary>Scan log</summary><pre id="jobOutput"></pre></details>
  </section>

  <section id="pickPanel" class="panel tab-panel" role="tabpanel" aria-labelledby="pickTab" hidden>
    <div class="panel-head">
      <div><h2>Pick episodes</h2><p class="notice">Tick up to six episodes for this poster. Picks are saved as you go, so reloading or rescanning keeps them.</p></div>
      <div class="controls"><button type="button" data-action="scan">Rescan feeds</button></div>
    </div>
    <div id="pickEmpty" class="empty-state" hidden>
      <h3 id="pickEmptyTitle">No episodes yet</h3>
      <p id="pickEmptyText">Scan your subscriptions to load their episodes.</p>
      <div class="controls"><button class="primary" type="button" data-action="scan" id="pickEmptyScan">Scan feeds</button><button type="button" data-go="subscriptions">Manage subscriptions</button></div>
    </div>
    <iframe id="candidates" title="Podcast episodes" src="/candidates"></iframe>
  </section>

  <section id="editPanel" class="panel tab-panel" role="tabpanel" aria-labelledby="editTab" hidden>
    <div class="panel-head">
      <div><h2>Edit poster text</h2><p class="notice">The summary and tags below are printed under each episode. Edits save automatically; use ↑ ↓ to set the poster order.</p></div>
      <div id="saveState" class="save-state" aria-live="polite"></div>
    </div>
    <p id="editAiHint" class="notice" hidden>AI suggestions are off. <button type="button" class="link-button" data-go="settings">Connect a model in Settings</button> to draft summaries and tags.</p>
    <div id="editEmpty" class="empty-state" hidden>
      <h3>No episodes on this poster yet</h3>
      <p>Pick up to six episodes first; their text shows up here for editing.</p>
      <div class="controls"><button class="primary" type="button" data-go="pick">Pick episodes</button></div>
    </div>
    <div id="editList" class="edit-list"></div>
  </section>

  <section id="posterPanel" class="panel tab-panel" role="tabpanel" aria-labelledby="posterTab" hidden>
    <div class="panel-head">
      <div><h2>Poster</h2><p class="notice" id="posterHint">Previewing never archives anything; only Generate &amp; archive adds the poster to History.</p></div>
      <div class="controls">
        <label class="layout-choice" for="posterLayout">Layout
          <select id="posterLayout"><option value="list">List poster</option><option value="single">Single episode</option></select>
        </label>
        <label class="layout-choice" for="posterTheme">Theme
          <select id="posterTheme"><option value="dark">Dark</option><option value="ink-saving">White (ink-saving)</option></select>
        </label>
        <a id="openPreview" class="download-link" href="/api/poster" target="_blank" rel="noopener noreferrer" title="Open the preview PDF in a new tab." hidden>Open preview PDF</a>
        <button class="primary" id="generatePoster" type="button">Generate &amp; archive</button>
      </div>
    </div>
    <div id="archivedBanner" class="banner" hidden aria-live="polite">
      <div><strong id="archivedTitle">Archived</strong><div class="notice" id="archivedMeta"></div></div>
      <div class="controls">
        <a id="archivedPrint" class="download-link" target="_blank" rel="noopener noreferrer" title="Open the PDF in a new tab, then choose Print in your PDF viewer.">Print PDF</a>
        <a id="archivedDownload" class="download-link">Download PDF</a>
        <button id="archivedPrinted" type="button">Mark printed</button>
        <button id="startNewPoster" class="primary" type="button">Start a new poster</button>
      </div>
    </div>
    <div id="posterEmpty" class="empty-state" hidden>
      <h3>Nothing to print yet</h3>
      <p>Pick up to six episodes and they will appear here as a poster preview.</p>
      <div class="controls"><button class="primary" type="button" data-go="pick">Pick episodes</button></div>
    </div>
    <div id="posterBody" class="preview-wrap">
      <iframe id="poster" title="Poster preview PDF" hidden></iframe>
      <div id="previewOverlay" class="preview-overlay" hidden><div id="previewMessage">Rendering preview…</div><div class="controls" style="justify-content:center"><button id="retryPreview" type="button" hidden>Try again</button><button type="button" data-go="edit" id="previewEditLink" hidden>Back to Edit text</button></div></div>
    </div>
  </section>

  <section id="subscriptionsPanel" class="panel tab-panel" role="tabpanel" aria-labelledby="subscriptionsTab" hidden>
    <div class="panel-head">
      <div><h2>Subscriptions</h2><p class="notice" id="subscriptionsStatus">Your subscriptions are stored locally in user-data. Import a list to start or maintain them.</p></div>
      <div class="controls">
        <label class="upload" for="opmlFile">Import OPML…</label>
        <input id="opmlFile" type="file" accept=".opml,.xml,application/xml,text/xml">
        <select id="opmlImportMode" aria-label="Import mode"><option value="merge" selected>Merge (keep existing, add new)</option><option value="replace">Replace current list</option></select>
        <a id="exportSubscriptions" class="download-link" href="/api/subscriptions/download" hidden>Export OPML</a>
        <button class="primary" type="button" data-action="scan">Scan feeds</button>
      </div>
    </div>
    <div id="subscriptionAiTools" class="controls subscription-batch" hidden>
      <label for="subscriptionBatchSize">Batch size</label>
      <input id="subscriptionBatchSize" type="number" min="1" value="10">
      <span class="notice" id="subscriptionMissingCount">Loading channel metadata status…</span>
      <button id="processMissingSubscriptions" type="button" disabled>Fill in with AI</button>
      <button id="stopSubscriptionBatch" type="button" hidden>Stop after current</button>
    </div>
    <p class="notice" id="subscriptionBatchStatus" aria-live="polite" hidden>Missing channel notes are filled in OPML order; OPML does not record when feeds were added.</p>
    <p class="notice" id="subscriptionAiHint" hidden>Channel notes and default tags help summaries and are inherited by episodes. Write them by hand below, or <button type="button" class="link-button" data-go="settings">connect a model in Settings</button> to fill them in.</p>
    <div id="subscriptionList" class="history-list" aria-live="polite"></div>
  </section>

  <section id="historyPanel" class="panel tab-panel" role="tabpanel" aria-labelledby="historyTab" hidden>
    <div class="panel-head">
      <div><h2>Poster history</h2><p class="notice">Every generated poster is archived here. Mark each one printed once it is up; episodes on earlier posters are flagged when picking.</p></div>
      <div class="controls"><button class="danger" id="clearHistory" type="button" disabled>Clear poster archive</button></div>
    </div>
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
      <div class="settings-actions"><button class="primary" id="saveLlmSettings" type="button">Save settings</button><button id="testLlmConnection" type="button" disabled>Test connection</button></div>
      <div id="llmTestHint" class="notice" aria-live="polite">Enter a base URL to enable the connection test.</div>
      <div id="llmConnectionStatus" class="notice" aria-live="polite"></div>
    </div>
    <details id="llmDiagnostics" class="settings-debug">
      <summary>Recent LLM diagnostics</summary>
      <p class="notice">The last 50 connection tests and suggestion attempts from this server session. Logs include endpoint host, model, timing, and status only—not episode text, model output, or API keys.</p>
      <button id="refreshLlmDiagnostics" type="button">Refresh diagnostics</button>
      <div id="llmDiagnosticsList" class="history-list" aria-live="polite"></div>
    </details>
    <p class="notice settings-debug">Subscriptions, drafts, and posters are stored under <code>user-data/</code> on this computer. The server only accepts connections from this computer.</p>
  </section>
</main>
<div id="tray" class="tray" hidden>
  <div class="tray-inner">
    <div class="tray-summary">
      <div id="trayThumbs" class="tray-thumbs" aria-hidden="true"></div>
      <div><strong id="trayCount">No episodes on this poster yet</strong><div class="notice tray-hint" id="trayHint">Tick episodes to add them.</div></div>
    </div>
    <div class="controls">
      <button id="trayClear" type="button" hidden>Clear</button>
      <button id="trayBack" type="button" data-go="pick" hidden>← Pick episodes</button>
      <button id="trayNext" class="primary" type="button" data-go="edit" disabled>Edit text →</button>
    </div>
  </div>
</div>
<div id="toasts" class="toasts" aria-live="polite"></div>
<script>
const TABS = ["pick", "edit", "poster", "subscriptions", "history", "settings"];
const MAX_SLOTS = 6;
const candidatesFrame = document.getElementById("candidates");
const pickEmpty = document.getElementById("pickEmpty");
const pickEmptyTitle = document.getElementById("pickEmptyTitle");
const pickEmptyText = document.getElementById("pickEmptyText");
const pickEmptyScan = document.getElementById("pickEmptyScan");
const selectionCount = document.getElementById("selectionCount");
const editList = document.getElementById("editList");
const editEmpty = document.getElementById("editEmpty");
const editAiHint = document.getElementById("editAiHint");
const saveState = document.getElementById("saveState");
const posterFrame = document.getElementById("poster");
const posterBody = document.getElementById("posterBody");
const posterEmpty = document.getElementById("posterEmpty");
const posterHint = document.getElementById("posterHint");
const previewOverlay = document.getElementById("previewOverlay");
const previewMessage = document.getElementById("previewMessage");
const retryPreviewButton = document.getElementById("retryPreview");
const previewEditLink = document.getElementById("previewEditLink");
const openPreview = document.getElementById("openPreview");
const generatePosterButton = document.getElementById("generatePoster");
const posterLayout = document.getElementById("posterLayout");
const posterTheme = document.getElementById("posterTheme");
const singleLayoutOption = posterLayout.querySelector('option[value="single"]');
const archivedBanner = document.getElementById("archivedBanner");
const archivedTitle = document.getElementById("archivedTitle");
const archivedMeta = document.getElementById("archivedMeta");
const archivedPrint = document.getElementById("archivedPrint");
const archivedDownload = document.getElementById("archivedDownload");
const archivedPrintedButton = document.getElementById("archivedPrinted");
const startNewPosterButton = document.getElementById("startNewPoster");
const tray = document.getElementById("tray");
const trayThumbs = document.getElementById("trayThumbs");
const trayCount = document.getElementById("trayCount");
const trayHint = document.getElementById("trayHint");
const trayClear = document.getElementById("trayClear");
const trayBack = document.getElementById("trayBack");
const trayNext = document.getElementById("trayNext");
const toasts = document.getElementById("toasts");
const jobPanel = document.getElementById("jobPanel");
const jobTitle = document.getElementById("jobTitle");
const jobState = document.getElementById("jobState");
const jobOutput = document.getElementById("jobOutput");
const jobLog = document.getElementById("jobLog");
const historyList = document.getElementById("historyList");
const clearHistoryButton = document.getElementById("clearHistory");
const subscriptionList = document.getElementById("subscriptionList");
const subscriptionsStatus = document.getElementById("subscriptionsStatus");
const exportSubscriptions = document.getElementById("exportSubscriptions");
const subscriptionAiTools = document.getElementById("subscriptionAiTools");
const subscriptionAiHint = document.getElementById("subscriptionAiHint");
const subscriptionBatchSize = document.getElementById("subscriptionBatchSize");
const subscriptionMissingCount = document.getElementById("subscriptionMissingCount");
const processMissingSubscriptionsButton = document.getElementById("processMissingSubscriptions");
const stopSubscriptionBatchButton = document.getElementById("stopSubscriptionBatch");
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
const panels = Object.fromEntries(TABS.map(name => [name, document.getElementById(`${name}Panel`)]));

let activeTab = null;
let statusSnapshot = null;
let llmFormInitialized = false;
let posterSettingsInitialized = false;
let llmReady = false;
let llmReason = "Enable the LLM connection in Settings.";
// The poster draft lives on the server (config "slots"); these mirror it.
let draftSlots = [];
let draftKeys = [];
let draftDetails = null;
let draftQueue = Promise.resolve();
let pendingMutations = 0;
let saveError = "";
const pendingSaves = new Map();
let previewFingerprint = null;
let previewTask = null;
let previewAgain = false;
let generating = false;
let scanning = false;
let currentSubscriptionFeeds = [];
let processingSubscriptionBatch = false;
let stopSubscriptionBatchRequested = false;
let candidateHistorySnapshot = null;
let candidateChannelMetadataSnapshot = null;
let candidateLlmSnapshot = null;

async function requestJson(path, options={}){
  const response = await fetch(path, options);
  let data = null;
  try{ data = await response.json(); }catch(error){ data = null; }
  if(!response.ok) throw new Error(data?.error || `Request failed (${response.status})`);
  return data;
}

function postJson(path, body={}){
  return requestJson(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
}

function notify(message, {kind="info", action=null, timeout=null}={}){
  if(!message) return;
  const item = document.createElement("div");
  item.className = `toast ${kind}`;
  item.setAttribute("role", kind === "error" ? "alert" : "status");
  const text = document.createElement("div");
  text.textContent = message;
  item.append(text);
  const close = () => item.remove();
  if(action){
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = action.label;
    button.addEventListener("click", () => { close(); action.run(); });
    item.append(button);
  }
  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "toast-close";
  dismiss.setAttribute("aria-label", "Dismiss");
  dismiss.textContent = "×";
  dismiss.addEventListener("click", close);
  item.append(dismiss);
  for(const existing of toasts.querySelectorAll(".toast")){
    if(existing.firstElementChild?.textContent === message) existing.remove();
  }
  toasts.append(item);
  while(toasts.children.length > 3) toasts.firstElementChild.remove();
  setTimeout(close, timeout ?? (kind === "error" ? 12000 : action ? 9000 : 4500));
}

function parseTags(value){
  const values = Array.isArray(value) ? value : String(value || "").split(",");
  const seen = new Set();
  return values.map(tag => String(tag).trim().replace(/^#+/, "").trim()).filter(tag => {
    const key = tag.toLowerCase();
    if(!tag || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
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

function slotKey(slot){
  return slot?.type === "latest" ? `latest:${slot.feed_url || ""}` : String(slot?.url || "");
}

function slotTitle(slot){
  return slot.type === "latest" ? `Newest episode of ${slot.show}` : slot.episode;
}

function artworkUrlForSlot(slot){
  const path = typeof slot?.artwork_path === "string" ? slot.artwork_path : "";
  return path ? `/cache/artwork/${encodeURIComponent(path.split("/").pop())}` : "";
}

function plural(count, word){
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

/* ---------- Navigation ---------- */

function navigate(name){
  if(!TABS.includes(name)) name = "pick";
  if(location.hash === `#${name}`) showTab(name);
  else location.hash = name;
}

window.addEventListener("hashchange", () => showTab(location.hash.slice(1)));

async function showTab(name){
  if(!TABS.includes(name)) name = "pick";
  const changed = activeTab !== name;
  activeTab = name;
  for(const button of document.querySelectorAll("[data-tab]")){
    button.setAttribute("aria-selected", String(button.dataset.tab === name));
  }
  for(const [panelName, panel] of Object.entries(panels)) panel.hidden = panelName !== name;
  renderTray();
  if(changed) window.scrollTo(0, 0);
  try{
    if(name === "pick") updatePickState();
    if(name === "edit") await showEdit();
    if(name === "poster") await showPoster();
    if(name === "history") await refreshHistory();
    if(name === "subscriptions") await refreshSubscriptions();
    if(name === "settings") await refreshStatus();
  }catch(error){
    notify(error.message, {kind:"error"});
  }
}

for(const button of document.querySelectorAll("[data-tab]")){
  button.addEventListener("click", () => navigate(button.dataset.tab));
}

document.addEventListener("click", event => {
  const target = event.target instanceof Element ? event.target.closest("[data-go], [data-action]") : null;
  if(!target || target.disabled) return;
  if(target.dataset.go) navigate(target.dataset.go);
  if(target.dataset.action === "scan") startScan();
});

/* ---------- Poster draft ---------- */

function applyDraftSlots(slots, keys, {syncFrame=true}={}){
  draftSlots = Array.isArray(slots) ? slots : [];
  draftKeys = Array.isArray(keys) ? keys : draftSlots.map(slotKey);
  updateDraftUi();
  if(syncFrame) postDraftToFrame();
}

function postDraftToFrame(){
  candidatesFrame.contentWindow?.postMessage({type:"draft", slots:draftSlots}, location.origin);
}

async function loadDraft({syncFrame=true}={}){
  const details = await requestJson("/api/draft");
  draftDetails = details;
  if(!posterSettingsInitialized){
    posterLayout.value = details.layout || "list";
    posterTheme.value = details.theme || "dark";
    posterSettingsInitialized = true;
  }
  applyDraftSlots(details.slots.map(entry => entry.slot), details.slots.map(entry => entry.key), {syncFrame});
  return details;
}

// Draft changes run one at a time so each response reflects every earlier change.
function mutateDraft(path, body, {syncFrame=true, quiet=false}={}){
  pendingMutations++;
  updateSaveState();
  const run = draftQueue.then(async () => {
    try{
      const result = await postJson(path, body);
      saveError = "";
      applyDraftSlots(result.slots, result.keys, {syncFrame});
      return result;
    }catch(error){
      saveError = error.message;
      if(!quiet) notify(error.message, {kind:"error"});
      await loadDraft().catch(() => {});
      throw error;
    }finally{
      pendingMutations--;
      updateSaveState();
    }
  });
  draftQueue = run.catch(() => {});
  return run;
}

function updateDraftUi(){
  const count = draftSlots.length;
  selectionCount.textContent = `${count}/${MAX_SLOTS}`;
  selectionCount.classList.toggle("full", count >= MAX_SLOTS);
  singleLayoutOption.disabled = count !== 1;
  renderTray();
  if(activeTab === "poster") renderPosterState();
}

function renderTray(){
  const onStep = activeTab === "pick" || activeTab === "edit";
  tray.hidden = !onStep;
  document.body.classList.toggle("has-tray", onStep);
  if(!onStep) return;
  const count = draftSlots.length;
  const thumbs = draftSlots.map(slot => {
    const url = artworkUrlForSlot(slot);
    const node = document.createElement(url ? "img" : "span");
    if(url){
      node.src = url;
      node.alt = "";
    } else node.textContent = "♫";
    node.title = `${slot.show} — ${slotTitle(slot)}`;
    return node;
  });
  for(let index = count; index < MAX_SLOTS; index++){
    const empty = document.createElement("span");
    empty.className = "tray-slot-empty";
    thumbs.push(empty);
  }
  trayThumbs.replaceChildren(...thumbs);
  trayCount.textContent = count ? `${count} of ${MAX_SLOTS} episodes on this poster` : "No episodes on this poster yet";
  if(activeTab === "pick"){
    trayHint.textContent = count >= MAX_SLOTS
      ? "The poster is full. Untick an episode to swap it out."
      : "Tick episodes to add them. Picks are saved as you go.";
    trayClear.hidden = count === 0;
    trayBack.hidden = true;
    trayNext.textContent = "Edit text →";
    trayNext.dataset.go = "edit";
  } else {
    trayHint.textContent = "Edits save automatically.";
    trayClear.hidden = true;
    trayBack.hidden = false;
    trayNext.textContent = "Preview poster →";
    trayNext.dataset.go = "poster";
  }
  trayNext.disabled = count === 0;
}

async function restoreDraft(slots){
  try{
    for(const slot of slots){
      if(slot.type === "fixed") await mutateDraft("/api/draft/add", {slot});
    }
    if(activeTab === "edit") await showEdit();
    notify("Restored.");
  }catch(error){ /* mutateDraft already reported it */ }
}

trayClear.addEventListener("click", async () => {
  const saved = draftSlots.slice();
  if(!saved.length) return;
  try{
    await mutateDraft("/api/draft/clear", {});
    notify(`Cleared ${plural(saved.length, "episode")} from this poster.`, {action:{label:"Undo", run:() => restoreDraft(saved)}});
  }catch(error){ /* reported */ }
});

/* ---------- Step 1: Pick ---------- */

function updatePickState(){
  const ready = Boolean(statusSnapshot?.candidates_ready);
  pickEmpty.hidden = ready;
  candidatesFrame.hidden = !ready;
  if(!ready){
    const hasSubscriptions = Boolean(statusSnapshot?.opml_exists);
    pickEmptyTitle.textContent = hasSubscriptions ? "No episodes loaded yet" : "Start by importing your subscriptions";
    pickEmptyText.textContent = hasSubscriptions
      ? "Scan your subscriptions to load every episode their feeds provide."
      : "Export an OPML file from AntennaPod (or any podcast app), import it under Subscriptions, then scan it here.";
    pickEmptyScan.hidden = !hasSubscriptions;
  }
}

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
  llmReady = settings.enabled === true && hasBaseUrl && hasModel;
  llmReason = !settings.enabled ? "Enable the LLM connection in Settings." : !hasBaseUrl ? "Set an LLM base URL in Settings." : !hasModel ? "Set a preferred model in Settings." : "";
  candidateLlmSnapshot = {enabled:llmReady, reason:llmReason};
  candidatesFrame.contentWindow?.postMessage({type:"llm-settings", settings:candidateLlmSnapshot}, location.origin);
  editAiHint.hidden = llmReady;
  updateSubscriptionBatchControls();
  for(const button of editList.querySelectorAll(".ai-suggest")){
    button.disabled = !llmReady;
    button.title = llmReady ? "Draft a summary and tags with your configured model" : llmReason;
  }
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
  const frame = candidatesFrame.contentWindow;
  if(candidateLlmSnapshot !== null) frame?.postMessage({type:"llm-settings", settings:candidateLlmSnapshot}, location.origin);
  if(candidateHistorySnapshot !== null) syncCandidateHistory(candidateHistorySnapshot);
  if(candidateChannelMetadataSnapshot !== null) frame?.postMessage({type:"channel-metadata", metadata:candidateChannelMetadataSnapshot}, location.origin);
  postDraftToFrame();
});

window.addEventListener("message", event => {
  if(event.origin !== location.origin || event.source !== candidatesFrame.contentWindow) return;
  const data = event.data || {};
  if(data.type === "draft-add" && data.slot){
    mutateDraft("/api/draft/add", {slot:data.slot}, {syncFrame:false}).catch(() => {});
  } else if(data.type === "draft-remove" && typeof data.key === "string"){
    mutateDraft("/api/draft/remove", {key:data.key}, {syncFrame:false}).catch(() => {});
  } else if(data.type === "draft-refresh"){
    // A hand-added link's details arrived after it was picked.
    loadDraft({syncFrame:false}).catch(() => {});
  } else if(data.type === "toast"){
    notify(String(data.message || ""));
  } else if(data.type === "frame-height"){
    candidatesFrame.style.height = `${Math.max(320, Math.ceil(Number(data.height) || 0))}px`;
  } else if(data.type === "scroll-top"){
    const top = candidatesFrame.getBoundingClientRect().top + window.scrollY - 90;
    window.scrollTo({top:Math.max(0, top)});
  }
});

/* ---------- Step 2: Edit ---------- */

function updateSaveState(){
  const busy = pendingMutations > 0 || pendingSaves.size > 0;
  saveState.classList.toggle("error", Boolean(saveError) && !busy);
  saveState.textContent = busy
    ? "Saving…"
    : saveError ? `Couldn't save: ${saveError}` : draftSlots.length ? "✓ All changes saved" : "";
}

function scheduleSave(key, field, getValue, delay=600){
  const id = `${key}\n${field}`;
  clearTimeout(pendingSaves.get(id)?.timer);
  const body = () => ({key, [field]:field === "tags" ? parseTags(getValue()) : getValue()});
  const run = () => {
    pendingSaves.delete(id);
    return mutateDraft("/api/draft/update", body(), {syncFrame:false, quiet:true}).catch(() => {});
  };
  pendingSaves.set(id, {timer:setTimeout(run, delay), run, body});
  updateSaveState();
}

async function flushEdits(){
  const runs = [...pendingSaves.values()];
  for(const pending of runs) clearTimeout(pending.timer);
  await Promise.all(runs.map(pending => pending.run()));
  await draftQueue;
}

async function showEdit(){
  await flushEdits();
  await loadDraft({syncFrame:false});
  if(activeTab === "edit") renderEditList();
}

function renderEditList(){
  // Text typed since the last save is newer than the server copy; carry it over.
  const unsaved = new Map();
  for(const card of editList.querySelectorAll(".edit-card")){
    for(const [field, selector] of [["summary", "textarea"], ["tags", ".tags-input"]]){
      const id = `${card.dataset.key}\n${field}`;
      if(pendingSaves.has(id)) unsaved.set(id, card.querySelector(selector).value);
    }
  }
  const entries = draftDetails?.slots || [];
  editAiHint.hidden = llmReady || !entries.length;
  editList.replaceChildren(...entries.map(buildEditCard));
  for(const card of editList.querySelectorAll(".edit-card")){
    for(const [field, selector] of [["summary", "textarea"], ["tags", ".tags-input"]]){
      const value = unsaved.get(`${card.dataset.key}\n${field}`);
      const input = card.querySelector(selector);
      if(value === undefined || !input) continue;
      input.value = value;
      input.dispatchEvent(new Event("input"));
    }
  }
  renumberEditCards();
  updateSaveState();
}

function renumberEditCards(){
  const cards = [...editList.children];
  cards.forEach((card, index) => {
    card.querySelector(".edit-show").textContent = `${index + 1}. ${card.dataset.show}`;
    card.querySelector(".move-up").disabled = index === 0;
    card.querySelector(".move-down").disabled = index === cards.length - 1;
  });
  editEmpty.hidden = cards.length > 0;
}

// Reorder and remove move the cards in place rather than re-rendering, so text
// being typed elsewhere (and keyboard focus) is never replaced.
async function moveDraftEntry(card, offset){
  const cards = [...editList.children];
  const position = cards.indexOf(card);
  const target = position + offset;
  if(position < 0 || target < 0 || target >= cards.length) return;
  editList.insertBefore(card, offset < 0 ? cards[target] : cards[target].nextSibling);
  renumberEditCards();
  const button = card.querySelector(offset < 0 ? ".move-up" : ".move-down");
  (button.disabled ? card.querySelector(offset < 0 ? ".move-down" : ".move-up") : button).focus();
  try{
    await mutateDraft("/api/draft/reorder", {keys:[...editList.children].map(item => item.dataset.key)}, {syncFrame:false});
  }catch(error){
    await showEdit();
  }
}

async function removeDraftEntry(card, entry){
  const title = slotTitle(entry.slot);
  try{
    await flushEdits();
    const removedSlot = draftSlots.find(slot => slotKey(slot) === entry.key) || entry.slot;
    card.remove();
    renumberEditCards();
    await mutateDraft("/api/draft/remove", {key:entry.key});
    notify(`Removed “${title}” from this poster.`, removedSlot.type === "fixed"
      ? {action:{label:"Undo", run:() => restoreDraft([removedSlot])}}
      : {});
  }catch(error){
    await showEdit();
  }
}

function buildEditCard(entry){
  const slot = entry.slot;
  const card = document.createElement("article");
  card.className = "edit-card";
  card.dataset.key = entry.key;
  card.dataset.show = slot.show;
  const artworkUrl = entry.artwork_url || artworkUrlForSlot(slot);
  const art = document.createElement(artworkUrl ? "img" : "div");
  art.className = "edit-art";
  if(artworkUrl){
    art.src = artworkUrl;
    art.alt = `Artwork for ${slot.show}`;
  } else {
    art.setAttribute("aria-hidden", "true");
    art.textContent = "♫";
  }
  const body = document.createElement("div");
  const head = document.createElement("div");
  head.className = "edit-head";
  const heading = document.createElement("div");
  const show = document.createElement("div");
  show.className = "edit-show";
  show.textContent = slot.show;
  const title = document.createElement("div");
  title.className = "edit-title";
  if(slot.url){
    const link = document.createElement("a");
    link.href = slot.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = slotTitle(slot);
    title.append(link);
  } else title.textContent = slotTitle(slot);
  const meta = document.createElement("div");
  meta.className = "edit-meta";
  meta.textContent = [slot.date, slot.duration].filter(Boolean).join(" · ");
  heading.append(show, title, meta);
  if(entry.previously_posted){
    const note = document.createElement("div");
    note.className = "posted-note";
    note.textContent = `Also on ${entry.previously_posted.edition}${entry.previously_posted.printed ? " (printed)" : " (not marked printed)"}`;
    heading.append(note);
  }
  const order = document.createElement("div");
  order.className = "edit-order";
  const label = slotTitle(slot);
  const up = document.createElement("button");
  up.type = "button";
  up.className = "move-up";
  up.textContent = "↑";
  up.title = "Move up the poster";
  up.setAttribute("aria-label", `Move “${label}” up`);
  up.addEventListener("click", () => moveDraftEntry(card, -1));
  const down = document.createElement("button");
  down.type = "button";
  down.className = "move-down";
  down.textContent = "↓";
  down.title = "Move down the poster";
  down.setAttribute("aria-label", `Move “${label}” down`);
  down.addEventListener("click", () => moveDraftEntry(card, 1));
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "danger";
  remove.textContent = "Remove";
  remove.setAttribute("aria-label", `Remove “${label}” from the poster`);
  remove.addEventListener("click", () => removeDraftEntry(card, entry));
  order.append(up, down, remove);
  head.append(heading, order);
  body.append(head);
  card.append(art, body);
  if(slot.type !== "fixed"){
    const note = document.createElement("p");
    note.className = "notice";
    note.textContent = "The newest episode is picked from the feed when the poster is generated, so there is no text to edit here.";
    body.append(note);
    return card;
  }

  const summaryField = document.createElement("label");
  summaryField.className = "field";
  summaryField.textContent = "Poster summary";
  const textarea = document.createElement("textarea");
  textarea.maxLength = 400;
  textarea.value = slot.summary || "";
  textarea.placeholder = "A sentence or two on why this episode is worth a listen.";
  summaryField.append(textarea);
  const summaryFoot = document.createElement("div");
  summaryFoot.className = "field-foot";
  const tools = document.createElement("div");
  tools.className = "field-tools";
  const aiButton = document.createElement("button");
  aiButton.type = "button";
  aiButton.className = "ai-suggest";
  aiButton.textContent = "Suggest with AI";
  const useAiDraft = document.createElement("button");
  useAiDraft.type = "button";
  useAiDraft.textContent = "Use saved AI draft";
  const resetSummary = document.createElement("button");
  resetSummary.type = "button";
  resetSummary.textContent = "Reset to feed text";
  tools.append(aiButton, useAiDraft, resetSummary);
  const count = document.createElement("span");
  count.className = "char-count";
  summaryFoot.append(tools, count);
  const feedback = document.createElement("div");
  feedback.className = "feedback";
  feedback.setAttribute("aria-live", "polite");

  const tagsField = document.createElement("label");
  tagsField.className = "field";
  tagsField.textContent = "Tags (comma-separated, printed as #hashtags)";
  const tagsInput = document.createElement("input");
  tagsInput.type = "text";
  tagsInput.className = "tags-input";
  tagsInput.maxLength = 500;
  tagsInput.value = (slot.tags || []).join(", ");
  tagsInput.placeholder = "Climate, Local news";
  tagsField.append(tagsInput);
  const tagsFoot = document.createElement("div");
  tagsFoot.className = "field-foot";
  const channelTags = Array.isArray(entry.channel_tags) ? entry.channel_tags : [];
  const channelHint = document.createElement("span");
  channelHint.className = "notice";
  channelHint.textContent = channelTags.length ? `Channel tags: ${channelTags.map(tag => `#${tag}`).join(" ")}` : "";
  const useChannelTags = document.createElement("button");
  useChannelTags.type = "button";
  useChannelTags.textContent = "Use channel tags";
  const tagTools = document.createElement("div");
  tagTools.className = "field-tools";
  tagTools.append(channelHint, useChannelTags);
  tagsFoot.append(tagTools);
  tagsFoot.hidden = !channelTags.length;
  body.append(summaryField, summaryFoot, tagsField, tagsFoot, feedback);

  const feedText = defaultPosterSummary(entry.description);
  const sameTags = (left, right) => parseTags(left).join("\n").toLowerCase() === parseTags(right).join("\n").toLowerCase();
  const refreshTools = () => {
    count.textContent = `${textarea.value.length}/400`;
    count.classList.toggle("near", textarea.value.length > 360);
    const aiDraft = entry.llm_suggestion;
    useAiDraft.hidden = !aiDraft || (aiDraft.summary === textarea.value && sameTags(aiDraft.tags, tagsInput.value));
    resetSummary.hidden = !feedText || feedText === textarea.value;
    useChannelTags.hidden = !channelTags.length || sameTags(channelTags, tagsInput.value);
    aiButton.disabled = !llmReady;
    aiButton.title = llmReady ? "Draft a summary and tags with your configured model" : llmReason;
  };
  const applyText = (summary, tags, message) => {
    const previous = {summary:textarea.value, tags:tagsInput.value};
    if(summary !== null) textarea.value = summary;
    if(tags !== null) tagsInput.value = tags;
    refreshTools();
    scheduleSave(entry.key, "summary", () => textarea.value, 0);
    scheduleSave(entry.key, "tags", () => tagsInput.value, 0);
    const undo = document.createElement("button");
    undo.type = "button";
    undo.className = "link-button";
    undo.textContent = "Undo";
    undo.addEventListener("click", () => {
      textarea.value = previous.summary;
      tagsInput.value = previous.tags;
      refreshTools();
      scheduleSave(entry.key, "summary", () => textarea.value, 0);
      scheduleSave(entry.key, "tags", () => tagsInput.value, 0);
      feedback.textContent = "Restored your previous text.";
    });
    feedback.replaceChildren(document.createTextNode(`${message} `), undo);
  };
  textarea.addEventListener("input", () => {
    refreshTools();
    scheduleSave(entry.key, "summary", () => textarea.value);
  });
  tagsInput.addEventListener("input", () => {
    refreshTools();
    scheduleSave(entry.key, "tags", () => tagsInput.value);
  });
  useAiDraft.addEventListener("click", () => {
    const aiDraft = entry.llm_suggestion;
    if(aiDraft) applyText(aiDraft.summary, parseTags(aiDraft.tags).join(", "), "Using the saved AI draft.");
  });
  resetSummary.addEventListener("click", () => applyText(feedText, null, "Summary reset to the feed's description."));
  useChannelTags.addEventListener("click", () => applyText(null, channelTags.join(", "), "Using the channel's default tags."));
  aiButton.addEventListener("click", async () => {
    aiButton.disabled = true;
    aiButton.textContent = "Asking the model…";
    feedback.textContent = "";
    try{
      const result = await postJson("/api/llm/suggest", {episode:{
        url:slot.url,
        show:slot.show,
        title:slot.episode,
        description:(entry.description || "").slice(0, 12000),
        channel_description:(entry.channel_description || "").slice(0, 400),
        channel_tags:channelTags.slice(0, 12),
        episode_tags:parseTags(tagsInput.value).slice(0, 12),
        current_summary:textarea.value.slice(0, 400),
      }});
      entry.llm_suggestion = {summary:result.summary, tags:result.tags, suggestion_version:result.suggestion_version};
      applyText(result.summary, result.tags.join(", "), "AI suggestion applied and saved.");
    }catch(error){
      feedback.textContent = `Suggestion failed: ${error.message} See Settings → Recent LLM diagnostics for details.`;
    }finally{
      aiButton.textContent = "Suggest with AI";
      refreshTools();
    }
  });
  refreshTools();
  return card;
}

/* ---------- Step 3: Poster ---------- */

function currentFingerprint(){
  return JSON.stringify([draftSlots, posterLayout.value, posterTheme.value]);
}

function showPreviewOverlay(message, {retry=false}={}){
  previewOverlay.hidden = false;
  previewMessage.textContent = message;
  retryPreviewButton.hidden = !retry;
  previewEditLink.hidden = !retry;
}

async function showPoster(){
  renderPosterState();
  await flushEdits();
  await loadDraft({syncFrame:false});
  if(activeTab !== "poster") return;
  renderPosterState();
  if(draftSlots.length && previewFingerprint !== currentFingerprint()) await refreshPreview();
}

function renderPosterState(){
  const count = draftSlots.length;
  posterEmpty.hidden = count > 0;
  posterBody.hidden = count === 0;
  if(posterLayout.value === "single" && count !== 1 && count > 0){
    posterLayout.value = "list";
    postJson("/api/poster/settings", {layout:"list"}).catch(() => {});
  }
  const archived = count ? draftDetails?.archived : null;
  archivedBanner.hidden = !archived;
  if(archived){
    const generatedAt = archived.generated_at ? new Date(archived.generated_at).toLocaleString() : "";
    archivedTitle.textContent = `✓ Archived as ${archived.edition || archived.title || "a poster"}`;
    archivedMeta.textContent = archived.printed_at
      ? `Generated ${generatedAt} · marked printed ${new Date(archived.printed_at).toLocaleDateString()}. Start a new poster when you are ready for the next one.`
      : `Generated ${generatedAt} · not marked printed yet. Print it, then mark it printed.`;
    archivedPrint.href = `/api/history/${encodeURIComponent(archived.manifest)}/pdf`;
    archivedDownload.href = `/api/history/${encodeURIComponent(archived.manifest)}/download`;
    archivedPrintedButton.textContent = archived.printed_at ? "Mark not printed" : "Mark printed";
  }
  generatePosterButton.disabled = count === 0 || Boolean(archived) || generating;
  generatePosterButton.textContent = generating ? "Generating…" : archived ? "Archived ✓" : "Generate & archive";
  generatePosterButton.title = archived ? "This exact poster is already archived. Change the episodes, text, layout, or theme to make a new version." : "";
  posterHint.textContent = !count
    ? "Previewing never archives anything; only Generate & archive adds the poster to History."
    : archived
      ? `${plural(count, "episode")}. This version is archived; any change makes a new version you can archive.`
      : `${plural(count, "episode")}. This is a preview; nothing is archived until you choose Generate & archive.`;
}

// Only one render runs at a time (the server allows one); changes made meanwhile
// trigger one more pass, and Generate waits for the current pass to finish.
function refreshPreview(){
  if(!draftSlots.length) return Promise.resolve();
  if(previewTask){
    previewAgain = true;
    return previewTask;
  }
  previewTask = renderPreviewUntilCurrent().finally(() => { previewTask = null; });
  return previewTask;
}

async function renderPreviewUntilCurrent(){
  do{
    previewAgain = false;
    const fingerprint = currentFingerprint();
    showPreviewOverlay("Rendering preview…");
    try{
      await postJson("/api/preview", {layout:posterLayout.value, theme:posterTheme.value});
    }catch(error){
      showPreviewOverlay(`Couldn't render the preview: ${error.message}`, {retry:true});
      return;
    }
    previewFingerprint = fingerprint;
    posterFrame.src = `/api/poster?refresh=${Date.now()}`;
    posterFrame.hidden = false;
    openPreview.hidden = false;
    previewOverlay.hidden = true;
  }while(previewAgain || (activeTab === "poster" && draftSlots.length && previewFingerprint !== currentFingerprint()));
}

async function changePosterSettings(){
  try{
    await postJson("/api/poster/settings", {layout:posterLayout.value, theme:posterTheme.value});
    await loadDraft({syncFrame:false});
    renderPosterState();
    await refreshPreview();
  }catch(error){ notify(error.message, {kind:"error"}); }
}

async function generatePoster(){
  if(!draftSlots.length || generating) return;
  generating = true;
  renderPosterState();
  try{
    await flushEdits();
    previewAgain = false;
    if(previewTask) await previewTask;
    showPreviewOverlay("Generating and archiving your poster…");
    const result = await postJson("/api/generate-current", {layout:posterLayout.value, theme:posterTheme.value});
    previewFingerprint = currentFingerprint();
    posterFrame.src = `/api/poster?refresh=${Date.now()}`;
    posterFrame.hidden = false;
    previewOverlay.hidden = true;
    await Promise.all([loadDraft({syncFrame:false}), refreshHistory()]);
    candidatesFrame.contentWindow?.postMessage({type:"refresh-shortlist"}, location.origin);
    notify(`Poster archived as ${result.history?.edition || "a new edition"}. Print it, then mark it printed.`);
  }catch(error){
    previewOverlay.hidden = true;
    notify(`Poster generation failed: ${error.message}`, {kind:"error"});
  }finally{
    generating = false;
    renderPosterState();
  }
}

async function startNewPoster(){
  const count = draftSlots.length;
  if(count && !draftDetails?.archived && !window.confirm(`Clear all ${plural(count, "episode")} and their edited text? This poster has not been archived.`)) return;
  try{
    await mutateDraft("/api/draft/clear", {});
    previewFingerprint = null;
    posterFrame.hidden = true;
    openPreview.hidden = true;
    navigate("pick");
    notify("Started a new poster. Pick up to six episodes.");
  }catch(error){ /* reported */ }
}

generatePosterButton.addEventListener("click", generatePoster);
retryPreviewButton.addEventListener("click", refreshPreview);
posterLayout.addEventListener("change", changePosterSettings);
posterTheme.addEventListener("change", changePosterSettings);
startNewPosterButton.addEventListener("click", startNewPoster);
archivedPrintedButton.addEventListener("click", async () => {
  const archived = draftDetails?.archived;
  if(!archived) return;
  try{
    await postJson("/api/history/printed", {manifest:archived.manifest, printed:!archived.printed_at});
    await Promise.all([loadDraft({syncFrame:false}), refreshHistory()]);
    renderPosterState();
  }catch(error){ notify(error.message, {kind:"error"}); }
});

/* ---------- Feed scans ---------- */

function updateScanButtons(){
  for(const button of document.querySelectorAll('[data-action="scan"]')){
    button.disabled = scanning;
    if(!button.dataset.label) button.dataset.label = button.textContent;
    button.textContent = scanning ? "Scanning…" : button.dataset.label;
  }
}

async function startScan(){
  if(scanning) return;
  scanning = true;
  updateScanButtons();
  jobPanel.hidden = false;
  jobPanel.classList.remove("failed");
  jobTitle.textContent = "Scanning your feeds…";
  jobState.textContent = "Starting…";
  jobOutput.textContent = "";
  try{
    const job = await postJson("/api/scan", {});
    while(true){
      const current = await requestJson(`/api/jobs/${job.job_id}`);
      const lines = current.output.filter(Boolean);
      jobOutput.textContent = current.output.join("\n");
      jobOutput.scrollTop = jobOutput.scrollHeight;
      jobState.textContent = lines.at(-1) || "Working…";
      if(current.status === "complete"){
        const summary = lines.find(line => line.startsWith("Scanned ")) || "Episode list refreshed.";
        jobTitle.textContent = "Scan complete";
        jobState.textContent = `${summary} Your poster picks were kept.`;
        await refreshStatus();
        candidatesFrame.src = `/candidates?refresh=${Date.now()}`;
        refreshSubscriptions().catch(() => {});
        notify(`Scan complete. ${summary}`);
        setTimeout(() => { if(!scanning && !jobLog.open) jobPanel.hidden = true; }, 6000);
        return;
      }
      if(current.status === "failed"){
        jobTitle.textContent = "Scan failed";
        jobPanel.classList.add("failed");
        jobLog.open = true;
        notify("Feed scan failed. See the scan log for details.", {kind:"error"});
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }catch(error){
    jobTitle.textContent = "Scan failed";
    jobPanel.classList.add("failed");
    jobState.textContent = error.message;
    notify(`Could not scan feeds: ${error.message}`, {kind:"error"});
  }finally{
    scanning = false;
    updateScanButtons();
  }
}

document.getElementById("hideJob").addEventListener("click", () => { jobPanel.hidden = true; });

/* ---------- Status and settings ---------- */

async function refreshStatus(){
  const data = await requestJson("/api/status");
  statusSnapshot = data;
  renderLlmSettings(data.llm);
  updatePickState();
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
  const settings = await postJson("/api/llm/settings", llmSettingsPayload());
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
    const result = await postJson("/api/llm/test", {test:true});
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

/* ---------- Subscriptions ---------- */

function subscriptionNeedsMetadata(feed){
  return !String(feed.channel_description || "").trim() || !Array.isArray(feed.tags) || feed.tags.length === 0;
}

function updateSubscriptionBatchControls(){
  const missingCount = currentSubscriptionFeeds.filter(subscriptionNeedsMetadata).length;
  const showTools = llmReady || processingSubscriptionBatch;
  subscriptionAiTools.hidden = !showTools || !currentSubscriptionFeeds.length;
  subscriptionBatchStatus.hidden = subscriptionAiTools.hidden;
  subscriptionAiHint.hidden = showTools || !currentSubscriptionFeeds.length;
  const maximum = missingCount;
  subscriptionMissingCount.textContent = missingCount
    ? `${plural(missingCount, "subscription")} missing a channel note or default tags.`
    : "All subscriptions have channel notes and default tags.";
  subscriptionBatchSize.max = String(Math.max(1, maximum));
  let requested = Number.parseInt(subscriptionBatchSize.value, 10);
  if(!Number.isFinite(requested) || requested < 1) requested = Math.min(10, Math.max(1, maximum));
  // Before the feed list loads there is nothing to clamp against; keep the default.
  if(maximum > 0) requested = Math.min(requested, maximum);
  subscriptionBatchSize.value = String(requested);
  processMissingSubscriptionsButton.textContent = missingCount
    ? `Fill in first ${Math.min(requested, missingCount)} of ${missingCount} with AI`
    : "Nothing missing";
  processMissingSubscriptionsButton.disabled = missingCount === 0 || processingSubscriptionBatch || !llmReady;
  subscriptionBatchSize.disabled = processingSubscriptionBatch || missingCount === 0;
  stopSubscriptionBatchButton.hidden = !processingSubscriptionBatch;
  stopSubscriptionBatchButton.disabled = stopSubscriptionBatchRequested;
}

async function processMissingSubscriptions(){
  if(processingSubscriptionBatch) return;
  const pending = currentSubscriptionFeeds.filter(subscriptionNeedsMetadata);
  if(!pending.length){
    updateSubscriptionBatchControls();
    return;
  }
  const batchSize = Math.max(1, Math.min(
    pending.length,
    Number.parseInt(subscriptionBatchSize.value, 10) || 10
  ));
  const batch = pending.slice(0, batchSize);
  const approved = window.confirm(
    `Process first ${batch.length} of ${pending.length} incomplete subscriptions? ` +
    "Channel context will be sent to the configured model and successful suggestions saved, one feed at a time. You can stop after the current feed."
  );
  if(!approved) return;

  processingSubscriptionBatch = true;
  stopSubscriptionBatchRequested = false;
  updateSubscriptionBatchControls();
  let savedCount = 0;
  let attemptedCount = 0;
  const failures = [];
  try{
    for(let index = 0; index < batch.length; index++){
      if(stopSubscriptionBatchRequested) break;
      const feed = batch[index];
      attemptedCount = index + 1;
      const progress = `${index + 1} of ${batch.length}`;
      subscriptionBatchStatus.textContent = `Processing ${progress}: ${feed.title}…`;
      try{
        const suggestion = await postJson("/api/llm/channel-suggest", {feed_url:feed.url});
        await postJson("/api/subscriptions/metadata", {
          feed_url:feed.url,
          channel_description:String(feed.channel_description || "").trim() || suggestion.channel_description,
          tags:Array.isArray(feed.tags) && feed.tags.length ? feed.tags : suggestion.tags
        });
        savedCount++;
      }catch(error){
        failures.push(`${feed.title}: ${error.message}`);
      }
      subscriptionBatchStatus.textContent = `Processed ${progress}; saved ${savedCount}${failures.length ? `, failed ${failures.length}` : ""}.${stopSubscriptionBatchRequested ? " Stopping…" : ""}`;
    }
    await refreshSubscriptions();
    const failureDetails = failures.length ? ` Failures: ${failures.slice(0, 3).join("; ")}${failures.length > 3 ? "; …" : ""}` : "";
    const stopped = stopSubscriptionBatchRequested && attemptedCount < batch.length;
    notify(stopped
      ? `Channel metadata processing stopped after the current subscription: saved ${savedCount} of ${attemptedCount}.${failureDetails}`
      : `Channel metadata processing finished: saved ${savedCount} of ${batch.length}.${failureDetails}`, {kind:failures.length ? "error" : "info"});
    subscriptionBatchStatus.textContent = stopped
      ? `Stopped after ${attemptedCount} of ${batch.length}; saved ${savedCount}, failed ${failures.length}.`
      : `Finished ${batch.length} requested; saved ${savedCount}, failed ${failures.length}.`;
  }catch(error){
    notify(`Channel metadata processing stopped: ${error.message}`, {kind:"error"});
    subscriptionBatchStatus.textContent = "Could not refresh the subscription list after processing.";
  }finally{
    processingSubscriptionBatch = false;
    stopSubscriptionBatchRequested = false;
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
    ? `${plural(data.feeds.length, "subscription")} in ${data.opml}. Import another OPML file to merge or replace this list, then scan feeds for new episodes.`
    : "No subscriptions yet. Import an OPML export from your podcast app to get started.";
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
    metadata.textContent = feed.channel_description || "No channel note yet.";
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
    editorSummary.textContent = "Edit channel note and tags";
    const descriptionLabel = document.createElement("label");
    descriptionLabel.textContent = "Channel description / editorial note (up to 400 characters; not printed)";
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
    const actions = document.createElement("div");
    actions.className = "controls";
    const suggestMetadata = document.createElement("button");
    suggestMetadata.type = "button";
    suggestMetadata.textContent = "Suggest with AI";
    suggestMetadata.hidden = !llmReady;
    suggestMetadata.title = "Use the configured LLM to suggest this channel's description and default tags. Review them, then save.";
    suggestMetadata.addEventListener("click", async () => {
      suggestMetadata.disabled = true;
      suggestMetadata.textContent = "Asking the model…";
      try{
        const suggestion = await postJson("/api/llm/channel-suggest", {feed_url:feed.url});
        description.value = suggestion.channel_description;
        tagsInput.value = suggestion.tags.join(", ");
        notify(`Suggested a note and tags for ${feed.title}. Review them, then save.`);
      }catch(error){ notify(`Could not suggest channel metadata: ${error.message}`, {kind:"error"}); }
      finally{
        suggestMetadata.disabled = false;
        suggestMetadata.textContent = "Suggest with AI";
      }
    });
    const saveMetadata = document.createElement("button");
    saveMetadata.type = "button";
    saveMetadata.className = "primary";
    saveMetadata.textContent = "Save note and tags";
    saveMetadata.addEventListener("click", async () => {
      saveMetadata.disabled = true;
      try{
        await postJson("/api/subscriptions/metadata", {
          feed_url:feed.url,
          channel_description:description.value,
          tags:tagsInput.value.split(",").map(tag => tag.trim()).filter(Boolean)
        });
        notify(`Saved channel note and tags for ${feed.title}.`);
        await refreshSubscriptions();
      }catch(error){ notify(`Could not save channel metadata: ${error.message}`, {kind:"error"}); }
      finally{ saveMetadata.disabled = false; }
    });
    actions.append(suggestMetadata, saveMetadata);
    editor.append(editorSummary, descriptionLabel, tagsLabel, actions);
    row.append(editor);
    subscriptionList.append(row);
  }
}

subscriptionBatchSize.addEventListener("input", updateSubscriptionBatchControls);
processMissingSubscriptionsButton.addEventListener("click", processMissingSubscriptions);
stopSubscriptionBatchButton.addEventListener("click", () => {
  stopSubscriptionBatchRequested = true;
  stopSubscriptionBatchButton.disabled = true;
  subscriptionBatchStatus.textContent = "Stopping after the current subscription finishes…";
});
document.getElementById("opmlFile").addEventListener("change", async event => {
  const file = event.target.files[0];
  if(!file) return;
  const mode = document.getElementById("opmlImportMode").value;
  if(mode === "replace" && !window.confirm("Replace your current subscription list with this OPML file?")){
    event.target.value = "";
    return;
  }
  try{
    const result = await requestJson(`/api/subscriptions?mode=${mode}`, {method:"POST", headers:{"Content-Type":"application/xml"}, body:await file.arrayBuffer()});
    await Promise.all([refreshSubscriptions(), refreshStatus()]);
    notify(`${mode === "merge" ? `Added ${result.added} new` : "Imported"} subscriptions; ${result.feeds} total in ${result.opml}. Scan your feeds to load their episodes.`, {action:{label:"Scan now", run:startScan}});
  }catch(error){ notify(`Could not import OPML: ${error.message}`, {kind:"error"}); }
  event.target.value = "";
});

/* ---------- History ---------- */

async function refreshHistory(){
  const records = await requestJson("/api/history");
  syncCandidateHistory(records);
  historyList.replaceChildren();
  clearHistoryButton.disabled = records.length === 0;
  if(!records.length){
    const empty = document.createElement("div");
    empty.className = "empty-state";
    const heading = document.createElement("h3");
    heading.textContent = "No posters archived yet";
    const text = document.createElement("p");
    text.textContent = "Posters land here when you choose Generate & archive in the Poster step.";
    empty.append(heading, text);
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
    const episodeCount = Array.isArray(record.slots) ? record.slots.length : 0;
    generated.textContent = `Generated ${new Date(record.generated_at).toLocaleString()} · ${plural(episodeCount, "episode")}`;
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
    const previewContainer = document.createElement("div");
    previewContainer.className = "history-preview";
    previewContainer.hidden = true;
    const preview = document.createElement("button");
    preview.type = "button";
    preview.textContent = "Preview PDF";
    preview.addEventListener("click", () => {
      if(!previewContainer.hidden){
        previewContainer.hidden = true;
        previewContainer.replaceChildren();
        preview.textContent = "Preview PDF";
        return;
      }
      const frame = document.createElement("iframe");
      frame.title = `Preview of ${record.edition || record.title || "poster"}`;
      frame.src = `/api/history/${encodeURIComponent(record.manifest)}/pdf?refresh=${Date.now()}`;
      previewContainer.replaceChildren(frame);
      previewContainer.hidden = false;
      preview.textContent = "Hide preview";
    });
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = record.printed_at ? "" : "primary";
    toggle.textContent = record.printed_at ? "Mark not printed" : "Mark printed";
    toggle.addEventListener("click", async () => {
      try{
        await postJson("/api/history/printed", {manifest:record.manifest, printed:!record.printed_at});
        await refreshHistory();
      }catch(error){ notify(error.message, {kind:"error"}); }
    });
    const regenerate = document.createElement("button");
    regenerate.type = "button";
    regenerate.textContent = "Regenerate PDF";
    regenerate.title = "Re-render this archived PDF with the current poster layout, using the same episodes and edition date.";
    regenerate.addEventListener("click", async () => {
      regenerate.disabled = true;
      regenerate.textContent = "Regenerating…";
      try{
        await postJson("/api/history/regenerate", {manifest:record.manifest});
        notify(`Regenerated the ${record.edition || record.title || "archived"} PDF.`);
      }catch(error){
        notify(error.message, {kind:"error"});
      }finally{
        regenerate.disabled = false;
        regenerate.textContent = "Regenerate PDF";
      }
    });
    const layoutSelect = document.createElement("select");
    layoutSelect.title = "Change this archived poster's layout.";
    layoutSelect.innerHTML = '<option value="list">List poster</option><option value="single">Single episode</option>';
    layoutSelect.value = record.layout === "single" ? "single" : "list";
    layoutSelect.querySelector('option[value="single"]').disabled = episodeCount !== 1;
    const themeSelect = document.createElement("select");
    themeSelect.title = "Change this archived poster's theme.";
    themeSelect.innerHTML = '<option value="dark">Dark</option><option value="ink-saving">White (ink-saving)</option>';
    themeSelect.value = record.theme === "ink-saving" ? "ink-saving" : "dark";
    const applySettings = document.createElement("button");
    applySettings.type = "button";
    applySettings.textContent = "Apply theme/layout";
    applySettings.title = "Re-render this same archived poster with the chosen theme and layout, keeping its episodes and edition date.";
    applySettings.addEventListener("click", async () => {
      applySettings.disabled = true;
      applySettings.textContent = "Applying…";
      try{
        await postJson("/api/history/update-settings", {manifest:record.manifest, layout:layoutSelect.value, theme:themeSelect.value});
        notify(`Updated the ${record.edition || record.title || "archived"} PDF.`);
        await refreshHistory();
      }catch(error){
        notify(error.message, {kind:"error"});
      }finally{
        applySettings.disabled = false;
        applySettings.textContent = "Apply theme/layout";
      }
    });
    const locationsContainer = document.createElement("div");
    locationsContainer.className = "history-locations";
    locationsContainer.hidden = true;
    const locationsToggle = document.createElement("button");
    locationsToggle.type = "button";
    locationsToggle.textContent = `Locations (${(record.locations || []).length})`;
    let locationsMap = null;
    locationsToggle.addEventListener("click", async () => {
      locationsContainer.hidden = !locationsContainer.hidden;
      if(locationsContainer.hidden || locationsMap) return;
      locationsContainer.replaceChildren();
      const hint = document.createElement("p");
      hint.className = "notice";
      hint.textContent = "Click the map to drop a pin for a spot you posted this poster at.";
      const mapDiv = document.createElement("div");
      mapDiv.className = "location-map";
      const list = document.createElement("div");
      list.className = "location-list";
      const knownContainer = document.createElement("div");
      knownContainer.className = "location-known";
      locationsContainer.append(hint, mapDiv, list, knownContainer);
      locationsMap = L.map(mapDiv, {center:[20, 0], zoom:2});
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(locationsMap);
      const markers = [];
      const knownMarkers = [];
      async function addKnownPlace(place){
        try{
          const updated = await postJson("/api/history/location/add", {manifest:record.manifest, text:place.text, lat:place.lat, lng:place.lng});
          record.locations = updated.locations || [];
          locationsToggle.textContent = `Locations (${record.locations.length})`;
          renderLocations(record.locations);
          renderKnown();
        }catch(error){ notify(error.message, {kind:"error"}); }
      }
      async function renderKnown(){
        let known;
        try{ known = await requestJson("/api/history/known-locations"); }
        catch(error){ known = []; }
        const used = new Set((record.locations || []).map(place => place.text.trim().toLowerCase()));
        const remaining = known.filter(place => !used.has(place.text.trim().toLowerCase()));
        for(const marker of knownMarkers) locationsMap.removeLayer(marker);
        knownMarkers.length = 0;
        for(const place of remaining){
          const marker = L.circleMarker([place.lat, place.lng], {
            radius: 8, color: "#4fd1c5", weight: 2, fillColor: "#4fd1c5", fillOpacity: 0.25,
            bubblingMouseEvents: false,
          }).addTo(locationsMap).bindTooltip(`${place.text} (click to add)`);
          marker.on("click", () => addKnownPlace(place));
          knownMarkers.push(marker);
        }
        knownContainer.replaceChildren();
        if(!remaining.length) return;
        const label = document.createElement("p");
        label.className = "notice";
        label.textContent = "Or add a place you've used before (also shown as rings on the map):";
        const chips = document.createElement("div");
        chips.className = "location-list";
        for(const place of remaining){
          const addKnown = document.createElement("button");
          addKnown.type = "button";
          addKnown.textContent = place.text;
          addKnown.addEventListener("click", () => addKnownPlace(place));
          chips.append(addKnown);
        }
        knownContainer.append(label, chips);
      }
      function renderLocations(locations){
        list.replaceChildren();
        for(const marker of markers) locationsMap.removeLayer(marker);
        markers.length = 0;
        locations.forEach((place, index) => {
          const marker = L.marker([place.lat, place.lng]).addTo(locationsMap).bindPopup(place.text);
          markers.push(marker);
          const item = document.createElement("div");
          item.className = "location-item";
          const label = document.createElement("span");
          label.textContent = place.text;
          const renameLocation = document.createElement("button");
          renameLocation.type = "button";
          renameLocation.textContent = "Rename";
          renameLocation.addEventListener("click", async () => {
            const text = window.prompt("Rename this spot:", place.text);
            if(!text || !text.trim() || text.trim() === place.text) return;
            try{
              const updated = await postJson("/api/history/location/rename", {manifest:record.manifest, index, text});
              record.locations = updated.locations || [];
              renderLocations(record.locations);
              renderKnown();
            }catch(error){ notify(error.message, {kind:"error"}); }
          });
          const removeLocation = document.createElement("button");
          removeLocation.type = "button";
          removeLocation.textContent = "Remove";
          removeLocation.addEventListener("click", async () => {
            try{
              const updated = await postJson("/api/history/location/remove", {manifest:record.manifest, index});
              record.locations = updated.locations || [];
              locationsToggle.textContent = `Locations (${record.locations.length})`;
              renderLocations(record.locations);
              renderKnown();
            }catch(error){ notify(error.message, {kind:"error"}); }
          });
          item.append(label, renameLocation, removeLocation);
          list.append(item);
        });
        if(locations.length) locationsMap.fitBounds(locations.map(place => [place.lat, place.lng]), {maxZoom:14, padding:[24, 24]});
      }
      locationsMap.on("click", async (event) => {
        const text = window.prompt("Label this spot (e.g. a venue or street name):");
        if(!text) return;
        try{
          const updated = await postJson("/api/history/location/add", {manifest:record.manifest, text, lat:event.latlng.lat, lng:event.latlng.lng});
          record.locations = updated.locations || [];
          locationsToggle.textContent = `Locations (${record.locations.length})`;
          renderLocations(record.locations);
          renderKnown();
        }catch(error){ notify(error.message, {kind:"error"}); }
      });
      renderLocations(record.locations || []);
      await renderKnown();
      if(!(record.locations || []).length){
        const knownCoords = knownMarkers.map(marker => marker.getLatLng());
        if(knownCoords.length) locationsMap.fitBounds(knownCoords, {maxZoom: 14, padding: [24, 24]});
        else locationsMap.setView([20, 0], 2);
      }
      requestAnimationFrame(() => locationsMap.invalidateSize());
    });
    actions.append(layoutSelect, themeSelect, applySettings, printPdf, download, preview, regenerate, toggle, locationsToggle);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = status === "pending" ? "" : "danger";
    remove.textContent = status === "pending" ? "Delete unprinted" : "Force delete";
    remove.addEventListener("click", async () => {
      const force = status !== "pending";
      const prompt = force
        ? `Force-delete ${record.edition || record.title || "this poster"}? This permanently removes its archived PDF and stops using it for episode warnings.`
        : "Permanently delete this unprinted PDF and its history entry? It will no longer be used to warn about previously posted episodes.";
      if(!window.confirm(prompt)) return;
      try{
        await postJson(force ? "/api/history/force-delete" : "/api/history/delete", {manifest:record.manifest, ...(force ? {confirm:true} : {})});
        notify(force ? "Poster force-deleted from history." : "Unprinted poster removed from history.");
        await refreshHistory();
      }catch(error){ notify(error.message, {kind:"error"}); }
    });
    actions.append(remove);
    row.append(title, generated, state, actions, previewContainer, locationsContainer);
    historyList.append(row);
  }
}

clearHistoryButton.addEventListener("click", async () => {
  if(!window.confirm("Permanently delete all archived poster PDFs and their printed/unprinted history records? This clears old-episode warnings. It does not delete subscriptions, episode lists, caches, your current poster draft, or the current poster PDF.")) return;
  try{
    const result = await postJson("/api/history/clear", {confirm:true});
    notify(`Cleared ${result.entries} archived poster records and ${result.pdfs} PDFs.`);
    await refreshHistory();
  }catch(error){ notify(error.message, {kind:"error"}); }
});

/* ---------- Start ---------- */

// Typing right before closing or reloading the tab still lands on the server.
window.addEventListener("pagehide", () => {
  for(const pending of pendingSaves.values()){
    clearTimeout(pending.timer);
    fetch("/api/draft/update", {
      method:"POST",
      keepalive:true,
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(pending.body())
    });
  }
  pendingSaves.clear();
});

async function init(){
  let status = null;
  try{
    status = await refreshStatus();
    await loadDraft();
  }catch(error){
    notify(error.message, {kind:"error"});
  }
  const requested = location.hash.slice(1);
  const initial = TABS.includes(requested) ? requested : status && !status.opml_exists ? "subscriptions" : "pick";
  history.replaceState(null, "", `#${initial}`);
  showTab(initial);
  Promise.all([refreshHistory(), refreshSubscriptions()]).catch(error => notify(error.message, {kind:"error"}));
}

init();
</script>
</body>
</html>'''

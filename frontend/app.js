const state = { page: 1, pageSize: 25, total: 0, withoutCoordinates: 0, selected: null };
const session = { details: new Map(), candidates: new Map(), pageFields: new Map(), outreach: new Map() };
let mapInstance;
let markerLayer;
let searchTimer;
const $ = (id) => document.getElementById(id);
const params = () => {
  const p = new URLSearchParams({ page: state.page, page_size: state.pageSize, sort_by: $("sort-by").value, sort_dir: $("sort-dir").value });
  ["q", "state", "postcode"].forEach((id) => { if ($(id).value) p.set(id, $(id).value); });
  return p;
};
const friendlyError = (error) => {
  const text = String(error.message || error);
  if (text.includes("source") || text.includes("unavailable") || text.includes("timeout")) return "The public source is slow or unavailable. Please retry.";
  if (text.includes("GROQ_API_KEY") || text.includes("missing")) return "AI is not configured. Add GROQ_API_KEY to .env, then retry.";
  if (text.includes("429") || text.toLowerCase().includes("rate")) return "The service is busy. Please wait briefly and retry.";
  if (text.includes("robots") || text.includes("blocked") || text.includes("too large") || text.includes("redirect")) return "This website cannot be fetched safely. Try another URL.";
  if (text.includes("temporarily unavailable") || text.includes("search")) return "No website results are available. Paste a URL manually.";
  return "Something went wrong. Please retry.";
};
const showRetry = (element, error, callback) => { element.innerHTML = `${escapeHtml(friendlyError(error))} <button type="button" class="inline-retry">Retry</button>`; element.querySelector("button").addEventListener("click", callback); };
async function load() {
  $("status").textContent = "Loading records…";
  try {
    const response = await fetch(`/api/practices?${params()}`);
    if (!response.ok) throw new Error(await response.text());
    const data = await response.json(); state.items = data.items; state.total = data.total; state.withoutCoordinates = data.without_coordinates;
    $("rows").innerHTML = data.items.map((p) => `<tr data-id="${p.id}"><td><strong>${escapeHtml(p.name || "not available")}</strong></td><td>${escapeHtml([p.suburb,p.state,p.postcode].filter(Boolean).join(", ") || "not available")}</td></tr>`).join("");
    document.querySelectorAll("tr[data-id]").forEach((row) => row.addEventListener("click", () => openDrawer(state.items.find((p) => p.id === Number(row.dataset.id)))));
    $("page").textContent = `${data.page} / ${Math.max(1, Math.ceil(data.total / data.page_size))}`;
    $("result-count").textContent = `${data.total.toLocaleString()} practices found`;
    $("result-subtitle").textContent = `${$("state").selectedOptions[0]?.textContent || "All states"} · sorted by ${$("sort-by").selectedOptions[0]?.textContent || "Practice name"}, ${$("sort-dir").value === "asc" ? "A–Z" : "Z–A"}`;
    $("showing").textContent = data.total ? `Showing ${(data.page - 1) * data.page_size + 1}–${Math.min(data.page * data.page_size, data.total)} of ${data.total.toLocaleString()}` : "";
    $("filter-summary").textContent = activeFilters() === "none" ? "No active filters" : `Active filters: ${activeFilters()}`;
    $("status").textContent = data.total ? "" : `No records match active filters: ${activeFilters()}.`;
    renderMap(data.items); updateExport(); loadStats();
  } catch (error) { showRetry($("status"), error, load); }
}
function activeFilters() { return [["search", $("q").value], ["state", $("state").value], ["postcode", $("postcode").value]].filter(([, value]) => value).map(([name, value]) => `${name}="${value}"`).join(", ") || "none"; }
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;" }[c])); }
function renderMap(items) {
  if (!mapInstance) {
    mapInstance = L.map("map").setView([-25.3,133.8], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution:"© OpenStreetMap contributors" }).addTo(mapInstance);
    markerLayer = L.layerGroup().addTo(mapInstance);
  }
  markerLayer.clearLayers();
  $("map-status").textContent = `${state.withoutCoordinates} record(s) not shown on map because coordinates are not available.`;
  items.filter((p) => p.lat !== null && p.lon !== null).forEach((p) => L.marker([p.lat,p.lon]).bindPopup(escapeHtml(p.name)).on("click", () => openDrawer(p)).addTo(markerLayer));
}
async function loadStats() {
  try {
    const data = await (await fetch("/api/stats")).json();
    $("headline-total").textContent = data.total.toLocaleString();
    const selected = $("state").value;
    $("state").innerHTML = `<option value="">All states (${data.total})</option>` + data.states.map((item) => `<option value="${escapeHtml(item.state)}">${escapeHtml(item.state)} (${item.count})</option>`).join("");
    $("state").value = selected;
  } catch (error) { showRetry($("stats"), error, loadStats); }
}
async function loadMetadata() {
  try { const data = await (await fetch("/api/metadata")).json(); $("source-info").innerHTML = data.ingested_at ? `Data snapshot ingested ${escapeHtml(new Date(data.ingested_at).toLocaleString())} from ${escapeHtml(data.source_name)} · <a href="${escapeHtml(data.source_url)}" target="_blank" rel="noopener">source link</a>` : `Data not loaded yet. <button id="load-data">Load data</button>`; if ($("load-data")) $("load-data").addEventListener("click", runIngest); } catch (error) { showRetry($("source-info"), error, loadMetadata); }
}
async function runIngest() { $("source-info").textContent = "Loading data… This may take a moment."; try { await request("/api/ingest", { method:"POST" }); await loadMetadata(); await loadStats(); await load(); } catch (error) { showRetry($("source-info"), error, runIngest); } }
function updateExport() { $("export").href = `/api/practices/export.csv?${params()}`; }
async function openDrawer(practice) {
  state.selected = practice; $("drawer").hidden = false; $("detail-name").textContent = practice.name || "not available"; $("detail-address").textContent = [practice.address,practice.suburb,practice.state,practice.postcode].filter(Boolean).join(", ") || "Address not available"; $("ai-status").textContent = ""; $("ai-output").textContent = ""; $("manual-url").value = "";
  try { const response = await fetch(`/api/practices/${practice.id}/details`); if (!response.ok) throw new Error(await response.text()); const details = await response.json(); session.details.set(practice.id, details); renderDetails(details, practice.id); } catch (error) { showRetry($("details"), error, () => openDrawer(practice)); }
}
function value(item) { return item === null || item === undefined || item === "" ? "not available" : item; }
function renderDetails(data, id) {
  const source = Object.entries(data.source_data || {}).map(([key, val]) => `<li><strong>${escapeHtml(key)}:</strong> ${escapeHtml(value(val))} <small>(Source data)</small></li>`).join("");
  const enrichment = session.pageFields.get(id) || data.enrichment;
  const enrichmentHtml = enrichment ? `<h3>Enrichment</h3><pre>${escapeHtml(JSON.stringify(enrichment, null, 2))}</pre><small>(Web page)</small>` : "";
  const candidates = session.candidates.get(id) || data.candidates || [];
  const candidateHtml = candidates.map((c, index) => `<div class="candidate"><a href="${escapeHtml(c.url)}" target="_blank" rel="noopener">${escapeHtml(c.url)}</a> · ${Math.round((c.confidence ?? c.ai_confidence ?? 0) * 100)}%<p>${escapeHtml(c.reason ?? c.ai_reason ?? "not available")}</p><button data-confirm="${index}">Confirm</button> <button data-reject="${index}">Reject</button></div>`).join("");
  const draft = session.outreach.get(id) || data.outreach;
  $("details").innerHTML = `<h3>Source fields <small>(Source data)</small></h3><ul>${source || "<li>not available</li>"}</ul>${enrichmentHtml}<h3>Website candidates <small>(AI-generated)</small></h3>${candidateHtml || "<p>not available</p>"}`;
  document.querySelectorAll("[data-confirm]").forEach((button) => button.addEventListener("click", () => { const candidate = candidates[button.dataset.confirm]; $("manual-url").value = candidate.url; $("ai-status").textContent = "Website selected. Click Enrich to fetch it."; }));
  document.querySelectorAll("[data-reject]").forEach((button) => button.addEventListener("click", () => button.parentElement.remove()));
  if (draft) showDraft(draft.subject, draft.body);
}
async function request(url, options = {}) { const response = await fetch(url, options); const data = await response.json(); if (!response.ok) throw new Error(data.detail || "Request failed"); return data; }
async function findWebsite() { $("ai-status").textContent = "Searching…"; try { const candidates = await request(`/api/practices/${state.selected.id}/find-website`, { method:"POST" }); session.candidates.set(state.selected.id, candidates); if (!candidates.length) $("ai-status").textContent = "No website results found. Paste a URL manually."; renderDetails(session.details.get(state.selected.id) || { source_data:{} }, state.selected.id); } catch (error) { $("ai-status").textContent = friendlyError(error); } }
async function enrich() { const url = $("manual-url").value.trim(); if (!url) { $("ai-status").textContent = "Confirm a candidate or paste a URL first."; return; } $("ai-status").textContent = "Enriching…"; try { const result = await request(`/api/practices/${state.selected.id}/enrich`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({website:url}) }); session.pageFields.set(state.selected.id, result); $("ai-status").textContent = "Enrichment saved."; renderDetails(session.details.get(state.selected.id) || { source_data:{} }, state.selected.id); } catch (error) { $("ai-status").textContent = friendlyError(error); } }
async function outreach() { $("ai-status").textContent = "Drafting…"; try { const draft = await request(`/api/practices/${state.selected.id}/outreach`, { method:"POST" }); session.outreach.set(state.selected.id, draft); showDraft(draft.subject, draft.body); $("ai-status").textContent = ""; } catch (error) { $("ai-status").textContent = friendlyError(error); } }
function showDraft(subject, body) { $("draft-label").hidden = false; $("draft-text").value = `Subject: ${subject}\n\n${body}`; }
async function ask() { $("ask-status").textContent = "Working…"; try { const data = await request("/api/ask", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({question:$("question").value}) }); $("ask-status").textContent = `Applied filter: ${Object.entries(data.filter).filter(([,v]) => v !== null).map(([k,v]) => `${k}=${v}`).join(", ") || "none"}`; $("q").value = data.filter.q || ""; $("state").value = data.filter.state || ""; $("postcode").value = data.filter.postcode || ""; state.page = 1; load(); } catch (error) { $("ask-status").textContent = friendlyError(error); } }
async function exportCsv(event) { event.preventDefault(); try { const response = await fetch($("export").href); if (!response.ok) throw new Error("source unavailable"); const blob = await response.blob(); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "practices.csv"; link.click(); if (response.headers.get("X-Export-Capped") === "true") $("status").textContent = "Export capped at the configured maximum row count."; } catch (error) { showRetry($("status"), error, exportCsv); } }
$("search").addEventListener("click", () => { state.page = 1; load(); }); $("q").addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => { state.page = 1; load(); }, 400); }); $("reset").addEventListener("click", () => { ["q","state","postcode"].forEach((id) => $(id).value = ""); state.page = 1; load(); }); $("sort-by").addEventListener("change", () => { state.page = 1; load(); }); $("sort-dir").addEventListener("change", () => { state.page = 1; load(); }); $("prev").addEventListener("click", () => { if (state.page > 1) { state.page--; load(); } }); $("next").addEventListener("click", () => { if (state.page * state.pageSize < state.total) { state.page++; load(); } }); $("ask").addEventListener("click", ask); $("export").addEventListener("click", exportCsv); $("copy-draft").addEventListener("click", () => navigator.clipboard.writeText($("draft-text").value)); $("close").addEventListener("click", () => $("drawer").hidden = true); $("find").addEventListener("click", findWebsite); $("enrich").addEventListener("click", enrich); $("outreach").addEventListener("click", outreach); loadMetadata(); load();

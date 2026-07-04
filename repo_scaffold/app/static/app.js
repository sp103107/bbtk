let lastBackupFile = null;
let backendOnline = false;
let ownerTokenSecurityState = null;
let ownerSessionToken = "";
let lastTechnicalReceipt = null;
let ownerLiveSocket = null;
let ownerLiveSocketPort = null;
let ownerLiveSocketToken = null;
let activeRosterState = [];
let activeRosterFilter = "all";
let expandedRosterEmployeeId = null;
const $ = (id) => document.getElementById(id);

function setBackendConnection(kind, title, detail){
  backendOnline = kind === "online" || kind === "warning";
  const banner = $("backend_connection_banner");
  const titleEl = $("backend_connection_title");
  const detailEl = $("backend_connection_detail");
  const health = $("health");
  const runtimeCard = $("runtime_card");
  document.body.dataset.backend = kind;
  if (banner) banner.className = `connection-banner ${kind}`;
  if (titleEl) titleEl.textContent = title;
  if (detailEl) detailEl.textContent = detail;
  if (health) health.textContent = title;
  if (runtimeCard) runtimeCard.className = `runtime-card operator-live-status ${kind}`;
  if (kind === "offline") setOfflineFlow("backend", "error");
  if (kind === "online" || kind === "warning") setOfflineFlow("backend", kind === "warning" ? "warning" : "done");
}


function setFlowStep(flow, step, state){
  document.querySelectorAll(`[data-flow="${flow}"]`).forEach(el => {
    el.classList.remove("active", "done", "warning", "error", "pending");
  });
  const target = document.querySelector(`[data-flow="${flow}"][data-step="${step}"]`);
  if (target) target.classList.add(state || "active");
}
function markFlowDoneUntil(flow, steps, activeStep, activeState){
  steps.forEach(step => {
    const el = document.querySelector(`[data-flow="${flow}"][data-step="${step}"]`);
    if (el) el.classList.remove("active", "done", "warning", "error", "pending");
  });
  const activeIndex = steps.indexOf(activeStep);
  steps.forEach((step, idx) => {
    const el = document.querySelector(`[data-flow="${flow}"][data-step="${step}"]`);
    if (!el) return;
    if (idx < activeIndex) el.classList.add("done");
    if (idx === activeIndex) el.classList.add(activeState || "active");
  });
}
function setEmployeeFlow(stage, state){
  markFlowDoneUntil("employee", ["id","pin","punch","receipt","synced"], stage || "id", state || "active");
}
function setOwnerFlow(stage, state){
  markFlowDoneUntil("owner", ["review","export","close","backup","verify"], stage || "review", state || "active");
}
function setOfflineFlow(stage, state){
  markFlowDoneUntil("offline", ["backend","local","sync","review","decision"], stage || "backend", state || "active");
}

function backendOfflinePayload(message){
  return { ok:false, error:"backend_unreachable", message: message || "Backend not connected. Start the Python server and open http://COMPUTER-IP:8080 from this device.", next_action:"Run python scripts/start_kiosk_server.py --host 0.0.0.0 --port 8080, then open the printed local network URL on this phone/tablet." };
}


function nowIsoLocalParts(){
  const d = new Date();
  return {
    time: d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
    day: d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" })
  };
}
function tickClock(){
  const p = nowIsoLocalParts();
  if ($("current_time")) $("current_time").textContent = p.time;
  if ($("business_day")) $("business_day").textContent = p.day;
}
tickClock(); setInterval(tickClock, 15000);

async function postJson(url, payload) {
  try {
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    let data;
    try { data = await res.json(); } catch { data = { ok:false, error:"invalid_json_response" }; }
    if (!res.ok) return { ok: false, status: res.status, data };
    return { ok: true, status: res.status, data };
  } catch (err) {
    const data = backendOfflinePayload(String(err && err.message ? err.message : err));
    setBackendConnection("offline", "Backend not connected", "Start the Python server, then open the local network URL on this device. Buttons cannot save punches from a file preview.");
    return { ok:false, status:0, data };
  }
}
function ownerToken(){ return ownerSessionToken || ($("owner_token") ? $("owner_token").value.trim() : ""); }
function renderOwnerSession(active, message){
  const form = $("operator_access_form");
  const status = $("operator_session_status");
  const hint = $("operator_access_hint");
  const lock = document.querySelector(".owner-lock");
  if (form) form.hidden = active;
  if (status) status.hidden = !active;
  if (hint) hint.textContent = message || (active
    ? "Owner access is active for this browser tab. The token field has been cleared."
    : "Enter the owner token once. It clears after validation and remains only in this browser tab's memory.");
  if (lock) lock.textContent = active ? "Owner Access Active" : "Owner Token Required";
  if ($("owner_console_state")) $("owner_console_state").textContent = active ? "Live Operations Unlocked" : "Awaiting Owner Token";
}
function lockOwnerSession(){
  ownerSessionToken = "";
  if ($("owner_token")) $("owner_token").value = "";
  if (ownerLiveSocket) ownerLiveSocket.close();
  ownerLiveSocket = null;
  ownerLiveSocketToken = null;
  renderOwnerSession(false, "Session locked. Enter the owner token to reconnect live operations.");
  setLiveTransportState(false);
}
async function unlockOwnerSession(){
  const input = $("owner_token");
  const token = input ? input.value.trim() : "";
  if (!token) {
    renderOwnerSession(false, "Enter the owner token to unlock live operations.");
    if (input) input.focus();
    return;
  }
  const button = $("unlock_owner_btn");
  if (button) { button.disabled = true; button.textContent = "Checking…"; }
  try {
    const res = await fetch("/api/owner/active-sessions", {cache:"no-store", headers:{"X-Owner-Token":token}});
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(friendlyError(data));
    ownerSessionToken = token;
    input.value = "";
    renderOwnerSession(true);
    applyLiveRoster(data);
    connectOwnerLive();
    ownerNotice("success", "Owner access unlocked. Live employee and guest status is connected.");
    renderOwnerActionSummary("success", "Live operations unlocked", "The owner token was accepted and removed from the visible field.", "Choose an operator task or review the onsite roster.");
  } catch (err) {
    input.value = "";
    renderOwnerSession(false, err && err.message ? err.message : "Owner token was not accepted.");
    input.focus();
  } finally {
    if (button) { button.disabled = false; button.textContent = "Unlock"; }
  }
}
function renderOwnerTokenSecurity(state){
  ownerTokenSecurityState = state;
  const badge = $("owner_token_status_badge");
  const guidance = $("owner_token_guidance");
  const button = $("generate_owner_token_btn");
  if (!badge || !guidance || !button) return;
  if (state && state.configured) {
    badge.className = "security-status ready";
    badge.textContent = "Token protected";
    guidance.textContent = "An owner token is configured. To replace it, enter the current token below, then choose Rotate & Save New Token.";
    button.textContent = "Rotate & Save New Token";
    button.disabled = false;
  } else if (state && state.local_request) {
    badge.className = "security-status required";
    badge.textContent = "Setup required";
    guidance.textContent = "Create the first owner token and 10 recovery tokens now. BBTC will generate and save them together—no settings file editing needed.";
    button.textContent = "Generate & Save Secure Token";
    button.disabled = false;
  } else if (state) {
    badge.className = "security-status blocked";
    badge.textContent = "Use server computer";
    guidance.textContent = "For safety, first-time token setup must be completed on the computer running BBTC. Open this owner console there.";
    button.textContent = "Generate on Server Computer";
    button.disabled = true;
  } else {
    badge.className = "security-status checking";
    badge.textContent = "Status unavailable";
    guidance.textContent = "BBTC could not check owner-token setup. Confirm the backend is running and try again.";
    button.disabled = true;
  }
  if (state && !state.configured) selectOwnerTask("security");
}
async function checkOwnerTokenSecurity(){
  try {
    const res = await fetch("/api/security/owner-token/status", { cache:"no-store" });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error("owner token status failed");
    renderOwnerTokenSecurity(data);
  } catch {
    renderOwnerTokenSecurity(null);
  }
}
async function copyPrivateText(text){
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const helper = document.createElement("textarea");
  helper.value = text;
  helper.setAttribute("readonly", "");
  helper.style.position = "fixed";
  helper.style.opacity = "0";
  document.body.appendChild(helper);
  helper.select();
  const copied = document.execCommand("copy");
  helper.remove();
  if (!copied) throw new Error("copy_not_available");
}
function saveOwnerTokenRecoveryNote(token){
  const note = [
    "BEST BUDS TIME CLOCK — PRIVATE OWNER TOKEN",
    "",
    `Saved: ${new Date().toLocaleString()}`,
    `Owner token: ${token}`,
    "",
    "Keep this file private. Anyone with this token can use owner actions.",
    "BBTC cannot display the configured token again.",
    "To replace it later, enter this current token and use Rotate & Save New Token."
  ].join("\n");
  const url = URL.createObjectURL(new Blob([note], {type:"text/plain;charset=utf-8"}));
  const link = document.createElement("a");
  link.href = url;
  link.download = "bbtc-owner-token-private-recovery.txt";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
function showGeneratedOwnerToken(token, title, message, nextStep){
  ownerSessionToken = token;
  $("owner_token").value = "";
  $("generated_owner_token").value = token;
  $("owner_token_once_panel").hidden = false;
  $("owner_token_copy_status").textContent = "Copy the new owner token or save its private recovery note before leaving this page.";
  renderOwnerTokenSecurity({ configured:true, local_request:true });
  ownerNotice("success", message);
  renderOwnerActionSummary("success", title, message, nextStep);
  renderOwnerSession(true, "New owner access is active for this browser tab. Save the one-time token shown in Security.");
}
function showGeneratedBackupTokens(tokens, statusMessage){
  $("generated_backup_tokens").value = tokens.join("\n");
  $("backup_tokens_once_panel").hidden = false;
  markOwnerCard(
    "backup_tokens_copy_status",
    statusMessage || "Recovery set ready. Download the private recovery file before leaving this page.",
    "success"
  );
}
function saveBackupTokenFile(tokens){
  const note = [
    "BEST BUDS TIME CLOCK — PRIVATE SINGLE-USE BACKUP TOKENS",
    "",
    `Generated: ${new Date().toLocaleString()}`,
    "Each token below can recover the owner account once.",
    "Generating a new set invalidates every token in this file.",
    "",
    ...tokens,
    "",
    "Keep this file private and separate from the computer running BBTC."
  ].join("\n");
  const url = URL.createObjectURL(new Blob([note], {type:"text/plain;charset=utf-8"}));
  const link = document.createElement("a");
  link.href = url;
  link.download = "bbtc-owner-backup-tokens-private.txt";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
function dateParams(){
  const params = new URLSearchParams();
  const start = $("start").value;
  const end = $("end").value;
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  params.set("owner_token", ownerToken());
  return params;
}
function show(id, obj){
  lastTechnicalReceipt = obj;
  const button = $("download_last_receipt_btn");
  if (button) button.disabled = !obj;
  const target = $(id);
  if (target) {
    const failed = obj && obj.ok === false;
    target.className = `owner-card-result ${failed ? "error" : "success"}`;
    target.textContent = failed ? friendlyError(obj) : "Action completed successfully.";
  }
}
function downloadLastTechnicalReceipt(){
  if (!lastTechnicalReceipt) return;
  const blob = new Blob([JSON.stringify(lastTechnicalReceipt, null, 2) + "\n"], {type:"application/json"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `bbtc-technical-receipt-${new Date().toISOString().replaceAll(":","-")}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
function ownerDownloadLink(kind, file, periodId){
  if (kind === "pay_period") return `/api/owner/pay_period/download?period_id=${encodeURIComponent(periodId)}&file=${encodeURIComponent(file)}&owner_token=${encodeURIComponent(ownerToken())}`;
  return `/api/owner/download?file=${encodeURIComponent(file)}&owner_token=${encodeURIComponent(ownerToken())}`;
}
function fmtStatus(value){
  if (!value) return "—";
  return String(value).replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
}

function actionLabel(eventType){
  const labels = { clock_in:"Clock In", clock_out:"Clock Out", break_start:"Start Break", break_end:"End Break" };
  return labels[eventType] || fmtStatus(eventType);
}
function setFocusCard(kind, title, detail){
  const t = $("employee-focus-title");
  const d = $("employee_action_guide");
  const p = $("employee_focus_status");
  if (t) t.textContent = title;
  if (d) d.textContent = detail;
  if (p) { p.textContent = fmtStatus(kind); p.className = `focus-status-pill ${kind}`; }
}
function setInputGuard(kind, text){
  const g = $("employee_input_guard");
  if (!g) return;
  g.className = `input-guard ${kind}`;
  g.textContent = text;
}
function updateTodayCard(summary, receipt){
  const hours = $("today_hours_value");
  const status = $("today_status_value");
  const last = $("today_last_punch_value");
  if (!hours || !status || !last) return;
  if (summary) {
    hours.textContent = `${Number(summary.net_work_hours || 0).toFixed(2)} h`;
    status.textContent = fmtStatus(summary.current_status || "ready");
  }
  if (receipt && receipt.captured_local) last.textContent = new Date(receipt.captured_local).toLocaleTimeString([], {hour:"numeric", minute:"2-digit"});
}
function renderLocalInputError(message){
  const card = $("employee_receipt");
  const title = card.querySelector(".receipt-title");
  const msg = card.querySelector(".receipt-message");
  const metrics = card.querySelector(".receipt-metrics");
  card.classList.remove("success", "neutral", "warning");
  card.classList.add("error");
  title.textContent = "Punch not sent";
  msg.textContent = message;
  metrics.hidden = true;
  const next = $("receipt_next");
  if (next) next.textContent = "Enter Employee ID and PIN, then try the intended punch again.";
  setEmployeeStrip("error", message);
  setFocusCard("error", "Action blocked", "Employee ID and PIN are required before this kiosk can record or locally save a punch.");
  setInputGuard("error", message);
  setEmployeeFlow("id", "error");
}
function validateEmployeeInputs(payload){
  if (!payload.employee_id && !payload.pin) return "Employee ID and PIN are required.";
  if (!payload.employee_id) return "Employee ID is required before tapping a punch button.";
  if (!payload.pin) return "PIN is required before tapping a punch button.";
  return null;
}
function friendlyError(data){
  const raw = data && (data.error || (data.punch_receipt && data.punch_receipt.policy_flags && data.punch_receipt.policy_flags[0]));
  const map = {
    employee_not_found: "Employee ID was not found. Check the ID or ask the owner.",
    invalid_pin: "PIN not accepted. Check your employee ID and PIN.",
    employee_inactive: "This employee is inactive. Ask the owner to review.",
    unauthorized: "Owner token was not accepted.",
    owner_token_invalid: "Owner token was not accepted.",
    owner_token_current_required_or_invalid: "Enter the current owner token before rotating it.",
    owner_token_initial_setup_local_only: "First-time token setup must be completed on the computer running BBTC.",
    owner_token_setup_required: "Generate the main owner token before creating backup tokens.",
    backup_token_required: "Paste one unused backup token first.",
    backup_token_invalid_or_used: "That backup token is invalid or has already been used.",
    factory_reset_confirmation_invalid: "Type RESET BBTC exactly before running Factory Reset.",
    factory_reset_local_computer_only: "Factory Reset must be run from the computer hosting BBTC.",
    factory_reset_backup_verification_failed: "The safety backup could not be verified, so no reset was performed.",
    not_found: "The requested action was not found.",
    unsupported_event_type: "That punch type is not supported.",
    non_json_response: "The runtime returned a non-JSON response. Ask the owner to review."
  };
  return map[raw] || (raw ? String(raw).replaceAll("_", " ") : "This punch was not recorded. Ask the owner/manager to review.");
}
function setEmployeeStrip(kind, text){
  const strip = $("employee_status_strip");
  if (!strip) return;
  strip.className = `status-strip ${kind}`;
  strip.innerHTML = `<span class="status-dot ${kind}" aria-hidden="true"></span><span>${text}</span>`;
}
function ownerNotice(kind, text){
  const n = $("owner_notice");
  if (!n) return;
  n.className = `owner-banner ${kind}`;
  n.textContent = text;
}
function inferOwnerNextStep(data, fallback){
  if (!data || !data.ok) return "Review the message, confirm the owner token, and retry only after correcting the issue.";
  if (data.export_file) return "Download the export link shown in the Payroll Exports card and review it before using it for payroll.";
  if (data.pay_period && data.pay_period.period_id) return "Download the closed pay-period package and review owner_review.md before payroll submission.";
  if (data.backup_file) return "Run Verify Backup + Restore Dry Run before relying on this backup.";
  if (data.restore_dry_run && data.restore_dry_run.status) return "Keep the verification receipt with the backup record.";
  if (data.receipts || data.sync_receipts) return "Review pending-owner-review offline recovery receipts before any payroll use.";
  return fallback || "Review the plain-language result and continue with the next owner task.";
}
function renderOwnerActionSummary(kind, title, message, nextStep){
  const card = $("owner_action_summary");
  if (!card) return;
  card.className = `owner-action-summary ${kind}`;
  const titleEl = card.querySelector(".owner-summary-title");
  const msgEl = card.querySelector(".owner-summary-message");
  const nextEl = card.querySelector(".owner-summary-next");
  if (titleEl) titleEl.textContent = title;
  if (msgEl) msgEl.textContent = message;
  if (nextEl) nextEl.textContent = nextStep;
  if ($("owner_console_state")) $("owner_console_state").textContent = kind === "success" ? "Action Complete" : kind === "warning" ? "Needs Review" : "Action Needs Attention";
  if ($("owner_last_action")) $("owner_last_action").textContent = title;
  if ($("owner_next_step")) $("owner_next_step").textContent = nextStep;
}
function renderOwnerResult(data, fallback){
  if (data && data.ok) {
    const next = inferOwnerNextStep(data, fallback);
    ownerNotice("success", fallback || "Owner action completed successfully.");
    renderOwnerActionSummary("success", "Owner action completed", fallback || "Owner action completed successfully.", next);
    setOwnerFlow("verify", "done");
  } else {
    const msg = friendlyError(data);
    ownerNotice("error", msg);
    renderOwnerActionSummary("error", "Owner action did not complete", msg, "Correct the issue before attempting the next owner task.");
    setOwnerFlow("review", "error");
  }
}
function markOwnerCard(cardId, text, kind="success"){
  const el = $(cardId);
  if (!el) return;
  el.className = `owner-card-result ${kind}`;
  el.textContent = text;
}
function validateOwnerTokenPresent(){
  if (!ownerToken()) {
    const message = "Owner token is required before running owner actions.";
    ownerNotice("error", message);
    renderOwnerActionSummary("error", "Owner token required", message, "Enter the owner token, then retry the selected owner task.");
    setOwnerFlow("review", "error");
    return false;
  }
  return true;
}
function updateOfflineUi(){
  if (!window.OfflineTimekeeper) return;
  const st = window.OfflineTimekeeper.status();
  const badge = $("offline_queue_badge");
  const status = $("offline_queue_status");
  if (badge) badge.textContent = `${st.pending_count} pending`;
  if (status) status.textContent = st.pending_count ? `Offline queue has ${st.pending_count} pending recovery item(s) on this device. Sync when the backend is connected.` : "No pending offline punches on this device. Offline recovery items are evidence only until synced and reviewed.";
}

function renderOfflineReceipt(item){
  updateTodayCard(null, null);
  const card = $("employee_receipt");
  const title = card.querySelector(".receipt-title");
  const msg = card.querySelector(".receipt-message");
  const metrics = card.querySelector(".receipt-metrics");
  const next = $("receipt_next");
  card.classList.remove("success", "error", "neutral");
  card.classList.add("warning");
  title.textContent = "Offline punch saved locally";
  msg.textContent = `${fmtStatus(item.event_type)} was saved on this device as recovery evidence. It is pending backend sync and owner review.`;
  metrics.hidden = false;
  $("receipt_hours").textContent = "Pending";
  $("receipt_status").textContent = "Pending Sync";
  $("receipt_time").textContent = new Date(item.captured_at_client_utc).toLocaleTimeString([], {hour:"numeric", minute:"2-digit"});
  if (next) next.textContent = "Do not clear this browser/device until the pending offline punch is synced or exported.";
  if ($("today_hours_value")) $("today_hours_value").textContent = "Pending";
  if ($("today_status_value")) $("today_status_value").textContent = "Pending Sync";
  if ($("today_last_punch_value")) $("today_last_punch_value").textContent = new Date(item.captured_at_client_utc).toLocaleTimeString([], {hour:"numeric", minute:"2-digit"});
  setFocusCard("warning", "Offline recovery saved", "The punch is stored on this device as recovery evidence and must be synced/reviewed before payroll use.");
  setEmployeeStrip("warning", `${fmtStatus(item.event_type)} saved offline · Pending owner review`);
  updateOfflineUi();
  setEmployeeFlow("receipt", "warning");
  setOfflineFlow("review", "warning");
}

function renderPunchReceipt(data){
  const card = $("employee_receipt");
  const title = card.querySelector(".receipt-title");
  const msg = card.querySelector(".receipt-message");
  const metrics = card.querySelector(".receipt-metrics");
  const next = $("receipt_next");
  const receipt = data && data.punch_receipt ? data.punch_receipt : null;
  card.classList.remove("success", "error", "neutral");
  if (!receipt) {
    card.classList.add("error");
    title.textContent = "Punch not recorded";
    msg.textContent = friendlyError(data);
    metrics.hidden = true;
    if (next) next.textContent = "Ask the owner/manager to review before trying repeatedly.";
    setFocusCard("error", "Punch not recorded", "Review the message, then correct Employee ID/PIN or ask the owner/manager.");
    setEmployeeStrip("error", msg.textContent);
    return;
  }
  if (receipt.accepted) {
    card.classList.add("success");
    title.textContent = `Success — ${receipt.event_label || "Punch accepted"}`;
  } else {
    card.classList.add("error");
    title.textContent = "Punch rejected";
  }
  msg.textContent = receipt.accepted ? (receipt.message || "Punch accepted.") : friendlyError(data);
  if (receipt.today_summary) {
    $("receipt_hours").textContent = `${Number(receipt.today_summary.net_work_hours || 0).toFixed(2)} h`;
    $("receipt_status").textContent = fmtStatus(receipt.today_summary.current_status);
    $("receipt_time").textContent = receipt.captured_local ? new Date(receipt.captured_local).toLocaleTimeString([], {hour: "numeric", minute: "2-digit"}) : "—";
    metrics.hidden = false;
    updateTodayCard(receipt.today_summary, receipt);
    if (next) next.textContent = receipt.accepted ? "You can step away once this success receipt is visible." : "This punch did not enter payroll review until corrected.";
    setFocusCard(receipt.accepted ? "success" : "error", receipt.accepted ? "Punch accepted" : "Punch rejected", receipt.accepted ? `${receipt.event_label || "Punch"} recorded. Today shows ${Number(receipt.today_summary.net_work_hours || 0).toFixed(2)} hours.` : "The punch was rejected. Review the message before retrying.");
    setInputGuard(receipt.accepted ? "success" : "error", receipt.accepted ? "Receipt visible. The employee may step away after confirming the message." : "Punch rejected. Correct the issue before retrying.");
    setEmployeeStrip(receipt.accepted ? "success" : "error", `${receipt.event_label || "Punch"} · Today: ${Number(receipt.today_summary.net_work_hours || 0).toFixed(2)} h · ${fmtStatus(receipt.today_summary.current_status)}`);
    setEmployeeFlow(receipt.accepted ? "synced" : "receipt", receipt.accepted ? "done" : "error");
  } else {
    metrics.hidden = true;
    setEmployeeStrip("error", msg.textContent);
  }
}

async function checkBackendHealth(){
  if (location.protocol === "file:") {
    setBackendConnection("offline", "Backend not connected", "This page is open as a file preview. Start the Python backend and open http://COMPUTER-IP:8080 from this device.");
    return;
  }
  try {
    const res = await fetch("/api/health", { cache:"no-store" });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error("health check failed");
    ownerLiveSocketPort = data.websocket && data.websocket.available ? data.websocket.port : null;
    const warnings = data.setup_warnings && data.setup_warnings.length ? ` Setup warnings: ${data.setup_warnings.join(", ")}` : "";
    setBackendConnection(warnings ? "warning" : "online", `Runtime v${data.version} online · ${data.site_id}`, `Backend is connected. Employee punches can be recorded.${warnings}`);
    connectOwnerLive();
  } catch (err) {
    ownerLiveSocketPort = null;
    setBackendConnection("offline", "Backend not connected", "Start the Python server, then open the local network URL on this phone/tablet. Try /api/health to confirm the backend is reachable.");
  }
}
checkBackendHealth();
checkOwnerTokenSecurity();
setInterval(checkBackendHealth, 30000);

const operatorAccessBar = document.querySelector(".operator-access-bar");
const liveSummaryPanel = $("timeclock_summary_panel");
if (operatorAccessBar && liveSummaryPanel) operatorAccessBar.insertAdjacentElement("afterend", liveSummaryPanel);
const ownerTaskGrid = document.querySelector(".operator-console-grid");
const ownerSecurityCard = document.querySelector(".owner-security-card");
if (ownerTaskGrid && ownerSecurityCard) ownerTaskGrid.appendChild(ownerSecurityCard);

function selectOwnerTask(group){
  const selected = group || "today";
  document.querySelectorAll(".owner-task-rail [data-task-filter]").forEach(button => {
    const active = button.dataset.taskFilter === selected;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  document.querySelectorAll("[data-owner-group]").forEach(section => {
    const groups = (section.dataset.ownerGroup || "").split(/\s+/);
    section.hidden = !groups.includes(selected);
  });
}
document.querySelectorAll(".owner-task-rail [data-task-filter]").forEach(button => {
  button.addEventListener("click", () => selectOwnerTask(button.dataset.taskFilter));
});
selectOwnerTask("today");

if ($("unlock_owner_btn")) $("unlock_owner_btn").addEventListener("click", unlockOwnerSession);
if ($("owner_token")) $("owner_token").addEventListener("keydown", event => {
  if (event.key === "Enter") {
    event.preventDefault();
    unlockOwnerSession();
  }
});
if ($("lock_owner_btn")) $("lock_owner_btn").addEventListener("click", lockOwnerSession);
if ($("download_last_receipt_btn")) $("download_last_receipt_btn").addEventListener("click", downloadLastTechnicalReceipt);

if ($("generate_owner_token_btn")) $("generate_owner_token_btn").addEventListener("click", async () => {
  const button = $("generate_owner_token_btn");
  if (!ownerTokenSecurityState) {
    await checkOwnerTokenSecurity();
    if (!ownerTokenSecurityState) return;
  }
  if (ownerTokenSecurityState.configured && !ownerToken()) {
    const message = "Enter the current owner token below before rotating it.";
    ownerNotice("error", message);
    renderOwnerActionSummary("error", "Current token required", message, "Enter the current token, then choose Rotate & Save New Token.");
    $("owner_token").focus();
    return;
  }
  if (ownerTokenSecurityState.configured && !window.confirm("Rotate the owner token now? The current token will stop working immediately.")) return;
  button.disabled = true;
  button.textContent = ownerTokenSecurityState.configured ? "Rotating Token…" : "Creating Secure Token…";
  const result = await postJson("/api/security/owner-token/generate", { owner_token: ownerToken() || null });
  if (result.ok && result.data && result.data.owner_token) {
    const token = result.data.owner_token;
    const initialBackupTokens = Array.isArray(result.data.backup_tokens) ? result.data.backup_tokens : [];
    showGeneratedOwnerToken(
      token,
      "Owner token ready",
      initialBackupTokens.length === 10
        ? "BBTC generated your owner token and first 10 single-use recovery tokens."
        : "BBTC generated, saved, and filled your new owner token.",
      initialBackupTokens.length === 10
        ? "Download the private recovery file now, then store it somewhere safe."
        : "Copy it or save the private recovery note before continuing."
    );
    if (initialBackupTokens.length === 10) {
      showGeneratedBackupTokens(
        initialBackupTokens,
        "First recovery set ready. Download the private recovery file before leaving this page."
      );
    }
    await checkBackendHealth();
  } else {
    const message = friendlyError(result.data);
    ownerNotice("error", message);
    renderOwnerActionSummary("error", "Owner token was not changed", message, "Correct the issue, then try again.");
    renderOwnerTokenSecurity(ownerTokenSecurityState);
  }
});
if ($("toggle_owner_token_btn")) $("toggle_owner_token_btn").addEventListener("click", () => {
  const input = $("owner_token");
  const button = $("toggle_owner_token_btn");
  const showing = input.type === "text";
  input.type = showing ? "password" : "text";
  button.textContent = showing ? "Show Entered Token" : "Hide Entered Token";
  button.setAttribute("aria-pressed", String(!showing));
});
if ($("copy_owner_token_btn")) $("copy_owner_token_btn").addEventListener("click", async () => {
  try {
    await copyPrivateText($("generated_owner_token").value);
    markOwnerCard("owner_token_copy_status", "Owner token copied. Keep the destination private.", "success");
  } catch {
    markOwnerCard("owner_token_copy_status", "Automatic copy was unavailable. Select and copy the token field above.", "warning");
    $("generated_owner_token").select();
  }
});
if ($("save_owner_token_note_btn")) $("save_owner_token_note_btn").addEventListener("click", () => {
  saveOwnerTokenRecoveryNote($("generated_owner_token").value);
  markOwnerCard("owner_token_copy_status", "Private recovery note saved. Move it to a secure location.", "success");
});
if ($("generate_backup_tokens_btn")) $("generate_backup_tokens_btn").addEventListener("click", async () => {
  if (!validateOwnerTokenPresent()) return;
  if (!window.confirm("Generate a new set of 10 backup tokens? Any older backup set will stop working immediately.")) return;
  const button = $("generate_backup_tokens_btn");
  button.disabled = true;
  button.textContent = "Generating 10 Backup Tokens…";
  const result = await postJson("/api/security/backup-tokens/generate", { owner_token: ownerToken() });
  button.disabled = false;
  button.textContent = "Generate New Set of 10";
  if (result.ok && result.data && Array.isArray(result.data.backup_tokens)) {
    const tokens = result.data.backup_tokens;
    showGeneratedBackupTokens(tokens, "New set ready. All older recovery tokens are now invalid.");
    ownerNotice("success", "10 single-use backup tokens generated. Save them before leaving this page.");
    renderOwnerActionSummary("success", "Backup tokens ready", "BBTC replaced the backup set and created 10 new single-use tokens.", "Copy all 10 or save the private backup file now.");
  } else {
    const message = friendlyError(result.data);
    markOwnerCard("backup_tokens_copy_status", message, "error");
    renderOwnerActionSummary("error", "Backup tokens were not generated", message, "Confirm the current owner token and try again.");
  }
});
if ($("copy_backup_tokens_btn")) $("copy_backup_tokens_btn").addEventListener("click", async () => {
  try {
    await copyPrivateText($("generated_backup_tokens").value);
    markOwnerCard("backup_tokens_copy_status", "All 10 backup tokens copied. Keep the destination private.", "success");
  } catch {
    $("generated_backup_tokens").select();
    markOwnerCard("backup_tokens_copy_status", "Automatic copy was unavailable. The token list is selected for manual copy.", "warning");
  }
});
if ($("save_backup_tokens_note_btn")) $("save_backup_tokens_note_btn").addEventListener("click", () => {
  const tokens = $("generated_backup_tokens").value.split(/\r?\n/).filter(Boolean);
  saveBackupTokenFile(tokens);
  markOwnerCard("backup_tokens_copy_status", "Private backup-token file saved. Store it securely.", "success");
});
if ($("recover_owner_token_btn")) $("recover_owner_token_btn").addEventListener("click", async () => {
  const raw = $("owner_backup_token").value.trim();
  const match = raw.match(/bbtc_backup_[A-Za-z0-9_-]+/);
  const backupToken = match ? match[0] : raw;
  if (!backupToken) {
    markOwnerCard("backup_recovery_status", "Paste one unused backup token first.", "error");
    $("owner_backup_token").focus();
    return;
  }
  if (!window.confirm("Use this backup token now? It will expire immediately and the current owner token will be replaced.")) return;
  const button = $("recover_owner_token_btn");
  button.disabled = true;
  button.textContent = "Recovering Owner Access…";
  const result = await postJson("/api/security/backup-tokens/recover", { backup_token: backupToken });
  button.disabled = false;
  button.textContent = "Recover & Create New Owner Token";
  if (result.ok && result.data && result.data.owner_token) {
    showGeneratedOwnerToken(
      result.data.owner_token,
      "Owner access recovered",
      "The backup token expired and BBTC created a new owner token.",
      `Save the new owner token now. ${result.data.backup_tokens_remaining} unused backup token(s) remain.`
    );
    $("owner_backup_token").value = "";
    markOwnerCard("backup_recovery_status", `Recovery complete. ${result.data.backup_tokens_remaining} unused backup token(s) remain.`, "success");
    await checkBackendHealth();
  } else {
    const message = friendlyError(result.data);
    markOwnerCard("backup_recovery_status", message, "error");
    renderOwnerActionSummary("error", "Owner recovery did not complete", message, "Try a different unused backup token or ask the local maintainer for help.");
  }
});

document.querySelectorAll("button[data-event]").forEach(btn => btn.addEventListener("click", async () => {
  const payload = { employee_id: $("employee_id").value.trim(), pin: $("pin").value.trim(), event_type: btn.dataset.event };
  const inputError = validateEmployeeInputs(payload);
  if (inputError) { renderLocalInputError(inputError); show("clock_result", {ok:false, local_validation:"blocked", error:inputError}); return; }
  btn.disabled = true;
  setFocusCard("pending", `${actionLabel(payload.event_type)} requested`, "Submitting punch. Keep this screen open until a receipt appears.");
  setEmployeeFlow("punch", "pending");
  setInputGuard("pending", "Submitting punch. Do not tap repeatedly.");
  const result = await postJson("/api/clock", payload);
  if (!result.ok && result.status === 0 && window.OfflineTimekeeper && payload.employee_id && payload.event_type) {
    const offlineItem = window.OfflineTimekeeper.savePunchIntent(payload);
    renderOfflineReceipt(offlineItem);
    show("clock_result", { ok:false, offline_saved:true, offline_item:offlineItem, non_claims:["Offline item is local recovery evidence only.", "PIN is not persisted in browser storage.", "Owner review is required before payroll counting."] });
  } else {
    renderPunchReceipt(result.data);
    show("clock_result", result.data);
  }
  btn.disabled = false;
}));


if (window.OfflineTimekeeper) {
  updateOfflineUi();
  window.addEventListener("offline-queue-change", updateOfflineUi);
  if ($("sync_offline_btn")) $("sync_offline_btn").addEventListener("click", async () => {
    try { const data = await window.OfflineTimekeeper.syncPending(); show("clock_result", data); ownerNotice("success", "Offline queue sync completed. Synced items are pending owner review."); }
    catch (err) { show("clock_result", {ok:false, error:String(err.message || err)}); ownerNotice("error", "Offline sync failed. Keep the local queue or download recovery exports."); }
    updateOfflineUi();
  });
  if ($("download_offline_jsonl_btn")) $("download_offline_jsonl_btn").addEventListener("click", () => window.OfflineTimekeeper.downloadPendingJsonl());
  if ($("download_offline_csv_btn")) $("download_offline_csv_btn").addEventListener("click", () => window.OfflineTimekeeper.downloadPendingCsv());
  if ($("clear_synced_offline_btn")) $("clear_synced_offline_btn").addEventListener("click", () => { window.OfflineTimekeeper.clearSynced(); updateOfflineUi(); });
}

function safeHtml(value){
  return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
}
function renderActiveSessions(sessions){
  const target = $("active_session_list");
  if (!target) return;
  activeRosterState = sessions || [];
  const visibleSessions = activeRosterFilter === "all"
    ? activeRosterState
    : activeRosterState.filter(session => (session.person_type || "employee") === activeRosterFilter);
  if (!visibleSessions.length) {
    const label = activeRosterFilter === "guest" ? "guests" : activeRosterFilter === "employee" ? "employees" : "employees or guests";
    target.innerHTML = `<div class="empty-manager-state">No ${label} are currently onsite.</div>`;
    return;
  }
  const observedAt = Date.now();
  target.innerHTML = visibleSessions.map(session => {
    const personType = session.person_type || "employee";
    const sessionId = personType === "guest" ? session.guest_session_id : session.employee_id;
    const detailsOpen = personType === "employee" && expandedRosterEmployeeId === session.employee_id;
    return `
    <article class="active-session-card person-${safeHtml(session.person_type || "employee")} ${session.requires_manager_review ? "warning" : ""}">
      <div class="roster-person"><strong>${safeHtml(session.display_name)}</strong><small>${safeHtml(session.person_type === "guest" ? (session.organization || session.purpose || "Visitor") : session.employee_id)} · ${safeHtml(fmtStatus(session.current_status))}</small>${session.requires_manager_review ? '<span class="review-pill">Needs manager review</span>' : ""}</div>
      <span class="person-type-pill">${safeHtml(session.person_type || "employee")}</span>
      <div class="active-timer" data-elapsed-seconds="${Number(session.elapsed_seconds || 0)}" data-observed-at="${observedAt}">00:00:00</div>
      <div class="roster-card-actions">
        ${personType === "employee" ? `<button type="button" class="tiny-action roster-details-btn" data-employee-id="${safeHtml(session.employee_id)}">${detailsOpen ? "Hide Information" : "View Information"}</button>` : ""}
        <button type="button" class="tiny-action roster-clockout-btn" data-person-type="${safeHtml(personType)}" data-session-id="${safeHtml(sessionId)}">${personType === "guest" ? "Sign Guest Out" : "Clock Out Employee"}</button>
      </div>
      ${detailsOpen ? `<div class="roster-details">
        <div><span>Employee ID</span><strong>${safeHtml(session.employee_id)}</strong></div>
        <div><span>Role</span><strong>${safeHtml(fmtStatus(session.employee_role || "employee"))}</strong></div>
        <div><span>Employee Status</span><strong>${safeHtml(fmtStatus(session.employee_status))}</strong></div>
        <div><span>Current Status</span><strong>${safeHtml(fmtStatus(session.current_status))}</strong></div>
        <div><span>Clocked In</span><strong>${safeHtml(new Date(session.clocked_in_at_local).toLocaleString())}</strong></div>
        <div><span>Elapsed</span><strong>${Number(session.elapsed_hours || 0).toFixed(2)} hours</strong></div>
      </div>` : ""}
    </article>`;
  }).join("");
  target.querySelectorAll(".roster-details-btn").forEach(button => button.addEventListener("click", () => {
    expandedRosterEmployeeId = expandedRosterEmployeeId === button.dataset.employeeId ? null : button.dataset.employeeId;
    renderActiveSessions(activeRosterState);
  }));
  target.querySelectorAll(".roster-clockout-btn").forEach(button => button.addEventListener("click", async () => {
    const personType = button.dataset.personType;
    const actionLabel = personType === "guest" ? "sign this guest out" : "clock this employee out with an owner adjustment";
    if (!window.confirm(`Are you sure you want to ${actionLabel}?`)) return;
    button.disabled = true;
    const result = await postJson("/api/owner/live/clock-out", {
      owner_token:ownerToken(),
      person_type:personType,
      session_id:button.dataset.sessionId
    });
    show("owner_result", result.data);
    if (result.data && result.data.ok) {
      const message = `${result.data.display_name} ${personType === "guest" ? "signed out" : "clocked out by owner"}.`;
      markOwnerCard("roster_action_result", message, "success");
      renderOwnerResult(result.data, message);
      if (result.data.live_roster) applyLiveRoster(result.data.live_roster);
    } else {
      button.disabled = false;
      markOwnerCard("roster_action_result", friendlyError(result.data), "error");
      renderOwnerResult(result.data, "Onsite action did not complete.");
    }
  }));
  tickActiveTimers();
}
function tickActiveTimers(){
  document.querySelectorAll(".active-timer").forEach(timer => {
    const base = Number(timer.dataset.elapsedSeconds || 0);
    const observed = Number(timer.dataset.observedAt || Date.now());
    const total = Math.max(Math.floor(base + (Date.now() - observed) / 1000), 0);
    const hours = String(Math.floor(total / 3600)).padStart(2, "0");
    const minutes = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
    const seconds = String(total % 60).padStart(2, "0");
    timer.textContent = `${hours}:${minutes}:${seconds}`;
  });
}
setInterval(tickActiveTimers, 1000);
function applyLiveRoster(data){
  if (!data) return;
  const roster = data.active_roster || (data.active_sessions || []).map(session => ({...session, person_type:"employee"}));
  renderActiveSessions(roster);
  if ($("manager_active_count")) $("manager_active_count").textContent = String(data.active_employee_count ?? (data.active_sessions || []).length);
  if ($("manager_guest_count")) $("manager_guest_count").textContent = String(data.active_guest_count ?? 0);
}
function setLiveTransportState(connected){
  const badge = $("live_transport_badge");
  if (!badge) return;
  badge.textContent = connected ? "Live WebSocket" : "Polling fallback";
  badge.className = connected ? "live-badge" : "live-badge fallback";
}
document.querySelectorAll(".onsite-tab").forEach(button => button.addEventListener("click", () => {
  activeRosterFilter = button.dataset.rosterFilter || "all";
  document.querySelectorAll(".onsite-tab").forEach(tabButton => {
    const active = tabButton === button;
    tabButton.classList.toggle("active", active);
    tabButton.setAttribute("aria-selected", String(active));
  });
  renderActiveSessions(activeRosterState);
}));
function connectOwnerLive(){
  const token = ownerToken();
  if (!ownerLiveSocketPort || !token || !window.WebSocket) {
    setLiveTransportState(false);
    return;
  }
  if (ownerLiveSocket && ownerLiveSocketToken === token && ownerLiveSocket.readyState <= WebSocket.OPEN) return;
  if (ownerLiveSocket) ownerLiveSocket.close();
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${scheme}://${location.hostname}:${ownerLiveSocketPort}/owner/live`);
  ownerLiveSocket = socket;
  ownerLiveSocketToken = token;
  socket.addEventListener("open", () => socket.send(JSON.stringify({type:"authenticate", owner_token:token})));
  socket.addEventListener("message", event => {
    try {
      const data = JSON.parse(event.data);
      if (!data.ok) {
        setLiveTransportState(false);
        socket.close();
        return;
      }
      if (data.message_type === "live_roster") {
        setLiveTransportState(true);
        applyLiveRoster(data);
      }
    } catch {
      setLiveTransportState(false);
    }
  });
  socket.addEventListener("close", () => {
    if (ownerLiveSocket === socket) ownerLiveSocket = null;
    setLiveTransportState(false);
  });
  socket.addEventListener("error", () => setLiveTransportState(false));
}
function renderSummaryPanel(data){
  applyLiveRoster(data);
  if ($("manager_completed_count")) $("manager_completed_count").textContent = String(data.completed_session_count || 0);
  if ($("manager_total_hours")) $("manager_total_hours").textContent = Number(data.total_hours || 0).toFixed(2);
  const rows = data.summaries || [];
  $("summary_table").innerHTML = rows.length ? `
    <table class="manager-table"><thead><tr><th>Employee</th><th>Net Hours</th><th>Regular Est.</th><th>OT Est.</th><th>Exceptions</th></tr></thead>
    <tbody>${rows.map(row => `<tr><td><strong>${safeHtml(row.display_name)}</strong><small>${safeHtml(row.employee_id)}</small></td><td>${Number(row.net_work_hours || 0).toFixed(2)}</td><td>${Number(row.regular_hours_estimate || 0).toFixed(2)}</td><td>${Number(row.overtime_hours_estimate || 0).toFixed(2)}</td><td>${safeHtml((row.exceptions || []).join(", ") || "None")}</td></tr>`).join("")}</tbody></table>`
    : '<div class="empty-manager-state">No accepted employee time entries in the selected range.</div>';
}
function renderEmployeeManagement(employees){
  const target = $("employee_management_table");
  if (!employees || !employees.length) {
    target.innerHTML = '<div class="empty-manager-state">No employees found.</div>';
    return;
  }
  target.innerHTML = `<table class="manager-table"><thead><tr><th>Employee</th><th>Role</th><th>Status</th><th>Rate</th><th>Tax Estimate</th><th>Actions</th></tr></thead><tbody>
    ${employees.map(employee => `<tr class="employee-row status-${safeHtml(employee.status)}">
      <td><strong>${safeHtml(employee.display_name)}</strong><small>${safeHtml(employee.employee_id)}</small></td>
      <td>${safeHtml(employee.role)}</td><td>${safeHtml(employee.status)}</td>
      <td>${employee.hourly_rate == null ? "—" : `$${Number(employee.hourly_rate).toFixed(2)}`}</td>
      <td>${employee.tax_withholding_percent == null ? "" : `${Number(employee.tax_withholding_percent).toFixed(2)}% `}${employee.tax_withholding_amount == null ? "" : `+ $${Number(employee.tax_withholding_amount).toFixed(2)}`}</td>
      <td class="employee-actions-cell">
        <button class="tiny-action employee-edit-btn" data-employee-id="${safeHtml(employee.employee_id)}">Edit</button>
        ${employee.status !== "inactive" ? `<button class="tiny-action employee-status-btn" data-employee-id="${safeHtml(employee.employee_id)}" data-status="inactive">Deactivate</button>` : ""}
        ${employee.status !== "active" ? `<button class="tiny-action employee-status-btn" data-employee-id="${safeHtml(employee.employee_id)}" data-status="active">Restore</button>` : ""}
        ${employee.status !== "removed" ? `<button class="tiny-action danger employee-status-btn" data-employee-id="${safeHtml(employee.employee_id)}" data-status="removed">Remove</button>` : ""}
      </td></tr>`).join("")}
    </tbody></table>`;
  target.querySelectorAll(".employee-edit-btn").forEach(button => button.addEventListener("click", () => {
    const employee = employees.find(item => item.employee_id === button.dataset.employeeId);
    if (!employee) return;
    $("new_employee_id").value = employee.employee_id;
    $("new_display_name").value = employee.display_name;
    $("new_pin").value = "";
    $("new_status").value = employee.status;
    $("new_role").value = employee.role;
    $("new_hourly_rate").value = employee.hourly_rate ?? "";
    $("new_tax_amount").value = employee.tax_withholding_amount ?? "";
    $("new_tax_percent").value = employee.tax_withholding_percent ?? "";
    $("new_employee_id").scrollIntoView({behavior:"smooth",block:"center"});
  }));
  target.querySelectorAll(".employee-status-btn").forEach(button => button.addEventListener("click", async () => {
    const status = button.dataset.status;
    const employeeId = button.dataset.employeeId;
    if (status === "removed" && !window.confirm(`Soft-remove ${employeeId}? Historical records will be preserved.`)) return;
    const result = await postJson("/api/owner/employees/status", {owner_token:ownerToken(),employee_id:employeeId,status});
    if (result.data && result.data.ok) await loadEmployeeManagement();
    else renderOwnerResult(result.data, "Employee status updated.");
  }));
}
async function loadEmployeeManagement(){
  if (!validateOwnerTokenPresent()) return;
  const res = await fetch("/api/owner/employees", {headers:{"X-Owner-Token":ownerToken()}});
  const data = await res.json();
  show("owner_result", data);
  renderOwnerResult(data, "Employee management loaded.");
  renderEmployeeManagement(data.employees || []);
  markOwnerCard("people_result_hint", data.ok ? "Employee management loaded below." : friendlyError(data), data.ok ? "success" : "error");
}
async function loadActiveSessions(){
  if (!ownerToken()) return;
  try {
    const res = await fetch("/api/owner/active-sessions", {cache:"no-store",headers:{"X-Owner-Token":ownerToken()}});
    if (!res.ok) return;
    const data = await res.json();
    applyLiveRoster(data);
    connectOwnerLive();
  } catch {}
}
setInterval(loadActiveSessions, 15000);
setInterval(connectOwnerLive, 5000);

$("summary_btn").addEventListener("click", async () => {
  if (!validateOwnerTokenPresent()) return;
  setOwnerFlow("review", "pending");
  const res = await fetch(`/api/owner/summary?${dateParams().toString()}`);
  const data = await res.json(); show("owner_result", data); renderOwnerResult(data, "Summary loaded. Review totals and active sessions below."); renderSummaryPanel(data); markOwnerCard("summary_result_hint", data.ok ? "Summary opened below with totals and active sessions." : friendlyError(data), data.ok ? "success" : "error");
  if (data.ok) {
    connectOwnerLive();
    $("timeclock_summary_panel").scrollIntoView({behavior:"smooth",block:"start"});
  }
});

$("export_btn").addEventListener("click", async () => {
  if (!validateOwnerTokenPresent()) return;
  setOwnerFlow("export", "pending");
  const payload = { owner_token: ownerToken(), format: $("format").value, start: $("start").value || null, end: $("end").value || null };
  const result = await postJson("/api/owner/export", payload);
  show("owner_result", result.data);
  renderOwnerResult(result.data, "Export generated. Use the download link before closing this session.");
  const slot = $("download_slot");
  if (result.data.ok && result.data.export_file) {
    const href = ownerDownloadLink("export", result.data.export_file);
    slot.innerHTML = `<a class="download" href="${href}">Download ${result.data.export_file}</a>`; markOwnerCard("release_result_hint", "Export generated; download link is visible in Payroll Exports.", "success");
  } else slot.innerHTML = "";
});

$("close_period_btn").addEventListener("click", async () => {
  if (!validateOwnerTokenPresent()) return;
  setOwnerFlow("close", "pending");
  const payload = { owner_token: ownerToken(), start: $("start").value || null, end: $("end").value || null, owner_note: $("owner_note").value || "" };
  const result = await postJson("/api/owner/pay_period/close", payload);
  show("owner_result", result.data);
  renderOwnerResult(result.data, "Pay period closed. Download and review the package before payroll submission.");
  const slot = $("period_download_slot");
  if (result.data.ok && result.data.pay_period && result.data.pay_period.period_id) {
    const pp = result.data.pay_period;
    const href = ownerDownloadLink("pay_period", `${pp.period_id}.zip`, pp.period_id);
    slot.innerHTML = `<a class="download" href="${href}">Download closed pay-period package</a>`; markOwnerCard("summary_result_hint", "Pay-period package generated. Review before payroll use.", "success");
  } else slot.innerHTML = "";
});

$("pay_periods_btn").addEventListener("click", async () => { if (!validateOwnerTokenPresent()) return; const res = await fetch(`/api/owner/pay_periods?owner_token=${encodeURIComponent(ownerToken())}`); const data=await res.json(); show("owner_result", data); renderOwnerResult(data, "Pay-period list loaded."); });
$("employees_btn").addEventListener("click", async () => {
  await loadEmployeeManagement();
  if (ownerToken()) $("employee_management_panel").scrollIntoView({behavior:"smooth",block:"start"});
});
if ($("guest_export_btn")) $("guest_export_btn").addEventListener("click", async () => {
  if (!validateOwnerTokenPresent()) return;
  const result = await postJson("/api/owner/guests/export", {owner_token:ownerToken()});
  show("owner_result", result.data);
  renderOwnerResult(result.data, "Separate guest CSV generated.");
  const slot = $("guest_download_slot");
  if (result.data && result.data.ok && result.data.export_file) {
    slot.innerHTML = `<a class="download" href="/api/owner/guests/download?file=${encodeURIComponent(result.data.export_file)}&owner_token=${encodeURIComponent(ownerToken())}">Download ${safeHtml(result.data.export_file)}</a>`;
  } else slot.textContent = "Guest export was not generated.";
});
$("backup_btn").addEventListener("click", async () => {
  if (!validateOwnerTokenPresent()) return;
  const result = await postJson("/api/owner/backup", { owner_token: ownerToken() });
  if (result.data && result.data.backup_file) { lastBackupFile = result.data.backup_file; if ($("backup_file")) $("backup_file").value = result.data.backup_file; }
  show("owner_result", result.data); renderOwnerResult(result.data, "Backup created. Run verify + restore dry run before relying on it."); markOwnerCard("backup_result_hint", result.data && result.data.ok ? "Backup created; verification still required." : friendlyError(result.data), result.data && result.data.ok ? "warning" : "error");
});
$("backup_verify_btn").addEventListener("click", async () => {
  if (!validateOwnerTokenPresent()) return;
  const file = ($("backup_file").value || lastBackupFile || "").trim();
  const result = await postJson("/api/owner/backup/verify", { owner_token: ownerToken(), backup_file: file, restore_dry_run: true });
  show("owner_result", result.data); renderOwnerResult(result.data, "Backup verified and restore dry run completed."); markOwnerCard("backup_result_hint", result.data && result.data.ok ? "Backup verification and restore dry run receipt created." : friendlyError(result.data), result.data && result.data.ok ? "success" : "error");
});
function resetOwnerScreen(){
  ownerSessionToken = "";
  lastTechnicalReceipt = null;
  if (ownerLiveSocket) ownerLiveSocket.close();
  ownerLiveSocket = null;
  ownerLiveSocketToken = null;
  activeRosterState = [];
  activeRosterFilter = "all";
  expandedRosterEmployeeId = null;
  document.querySelectorAll(".owner-panel input:not([readonly]), .owner-panel textarea:not([readonly])").forEach(input => { input.value = ""; });
  document.querySelectorAll(".onsite-tab").forEach(button => {
    const active = button.dataset.rosterFilter === "all";
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  if ($("manager_active_count")) $("manager_active_count").textContent = "0";
  if ($("manager_guest_count")) $("manager_guest_count").textContent = "0";
  if ($("manager_completed_count")) $("manager_completed_count").textContent = "0";
  if ($("manager_total_hours")) $("manager_total_hours").textContent = "0.00";
  if ($("active_session_list")) $("active_session_list").innerHTML = '<div class="empty-manager-state">Enter the owner token and open the summary.</div>';
  if ($("summary_table")) $("summary_table").innerHTML = "No summary loaded.";
  if ($("employee_management_table")) $("employee_management_table").textContent = "Enter the owner token and choose Manage Employees.";
  if ($("owner_token")) $("owner_token").value = "";
  if ($("download_last_receipt_btn")) $("download_last_receipt_btn").disabled = true;
  if ($("owner_result")) $("owner_result").textContent = "Owner result appears hereâ€¦";
  markOwnerCard("factory_reset_result", "Screen reset complete. No employee, guest, or timeclock data was changed.", "success");
  renderOwnerActionSummary("neutral", "Owner screen reset", "Browser-only fields and results were cleared.", "Enter the owner token when you are ready to continue.");
  renderOwnerSession(false, "Screen reset complete. Enter the owner token to reconnect live operations.");
  setLiveTransportState(false);
}
if ($("reset_screen_btn")) $("reset_screen_btn").addEventListener("click", resetOwnerScreen);
if ($("factory_reset_btn")) $("factory_reset_btn").addEventListener("click", async () => {
  if (!validateOwnerTokenPresent()) return;
  const phrase = $("factory_reset_phrase").value.trim();
  if (phrase !== "RESET BBTC") {
    markOwnerCard("factory_reset_result", "Type RESET BBTC exactly before running Factory Reset.", "error");
    $("factory_reset_phrase").focus();
    return;
  }
  if (!window.confirm("Factory Reset will clear all runtime employees, punches, guests, exports, and operational records after creating a verified backup. Continue?")) return;
  if (!window.confirm("Final confirmation: factory reset BBTC runtime data now?")) return;
  const button = $("factory_reset_btn");
  button.disabled = true;
  button.textContent = "Creating Backup + Resettingâ€¦";
  const result = await postJson("/api/owner/factory-reset", {
    owner_token:ownerToken(),
    confirmation:phrase
  });
  show("owner_result", result.data);
  if (result.data && result.data.ok) {
    $("factory_reset_phrase").value = "";
    applyLiveRoster(result.data.live_roster || {});
    if ($("manager_completed_count")) $("manager_completed_count").textContent = "0";
    if ($("manager_total_hours")) $("manager_total_hours").textContent = "0.00";
    if ($("summary_table")) $("summary_table").innerHTML = '<div class="empty-manager-state">Factory reset complete. Open the summary to load the fresh seed state.</div>';
    const message = `Factory reset complete. Verified backup: ${result.data.backup_file}`;
    markOwnerCard("factory_reset_result", message, "success");
    renderOwnerResult(result.data, message);
  } else {
    markOwnerCard("factory_reset_result", friendlyError(result.data), "error");
    renderOwnerResult(result.data, "Factory reset did not run.");
  }
  button.disabled = false;
  button.textContent = "Factory Reset Runtime";
});
$("add_employee_btn").addEventListener("click", async () => {
  const payload = {
    owner_token: ownerToken(),
    employee_id: $("new_employee_id").value.trim(),
    display_name: $("new_display_name").value.trim(),
    pin: $("new_pin").value.trim(),
    status: $("new_status").value,
    role: $("new_role").value,
    hourly_rate: $("new_hourly_rate").value,
    tax_withholding_amount: $("new_tax_amount").value,
    tax_withholding_percent: $("new_tax_percent").value
  };
  const result = await postJson("/api/owner/employees", payload);
  show("employee_result", result.data); renderOwnerResult(result.data, "Employee saved. Have them test a punch during setup.");
  if (result.data && result.data.ok) await loadEmployeeManagement();
});
if ($("manual_hours_btn")) $("manual_hours_btn").addEventListener("click", async () => {
  if (!validateOwnerTokenPresent()) return;
  const result = await postJson("/api/owner/manual-hours", {
    owner_token:ownerToken(),
    employee_id:$("manual_employee_id").value.trim(),
    work_date:$("manual_work_date").value,
    hours:$("manual_hours").value,
    reason:$("manual_reason").value.trim()
  });
  show("employee_result", result.data);
  renderOwnerResult(result.data, "Manual hours adjustment recorded for export review.");
});
$("review_btn").addEventListener("click", async () => { if (!validateOwnerTokenPresent()) return; const res = await fetch(`/api/owner/review?${dateParams().toString()}`); const data=await res.json(); show("owner_result", data); renderOwnerResult(data, "Manager review loaded. Resolve flags before payroll close."); markOwnerCard("people_result_hint", data.ok ? "Manager review loaded; resolve flags before close." : friendlyError(data), data.ok ? "warning" : "error"); });
$("adjustment_btn").addEventListener("click", async () => {
  const payload = { owner_token: ownerToken(), employee_id: $("adjust_employee_id").value.trim(), event_type: $("adjust_event_type").value, captured_at_utc: $("adjust_captured_at_utc").value.trim(), reason: $("adjust_reason").value.trim(), owner_note: $("adjust_owner_note").value.trim() };
  const result = await postJson("/api/owner/adjustment", payload);
  show("adjustment_result", result.data); renderOwnerResult(result.data, "Owner adjustment recorded. Review it before payroll close.");
});

function pilotDownloadLink(file, packId){ return `/api/owner/pilot/download?pack_id=${encodeURIComponent(packId)}&file=${encodeURIComponent(file)}&owner_token=${encodeURIComponent(ownerToken())}`; }
$("pilot_readiness_btn").addEventListener("click", async () => { const result = await postJson("/api/owner/pilot/readiness", { owner_token: ownerToken() }); show("pilot_result", result.data); renderOwnerResult(result.data, "Pilot readiness generated."); });
$("pilot_issues_btn").addEventListener("click", async () => { const res = await fetch(`/api/owner/pilot/issues?owner_token=${encodeURIComponent(ownerToken())}`); const data=await res.json(); show("pilot_result", data); renderOwnerResult(data, "Pilot issue list loaded."); });
$("pilot_issue_btn").addEventListener("click", async () => {
  const payload = { owner_token: ownerToken(), severity: $("pilot_issue_severity").value, title: $("pilot_issue_title").value.trim(), details: $("pilot_issue_details").value.trim(), status: "open" };
  const result = await postJson("/api/owner/pilot/issue", payload); show("pilot_result", result.data); renderOwnerResult(result.data, "Pilot issue logged.");
});
$("pilot_signoff_btn").addEventListener("click", async () => {
  const payload = { owner_token: ownerToken(), signer_name: $("pilot_signer_name").value.trim(), signoff_role: "owner", decision: $("pilot_decision").value, notes: $("pilot_owner_note").value.trim() };
  const result = await postJson("/api/owner/pilot/signoff", payload); show("pilot_result", result.data); renderOwnerResult(result.data, "Pilot sign-off recorded.");
});
$("pilot_pack_btn").addEventListener("click", async () => {
  const result = await postJson("/api/owner/pilot/package", { owner_token: ownerToken(), owner_note: $("pilot_owner_note").value.trim() });
  show("pilot_result", result.data); renderOwnerResult(result.data, "Pilot acceptance package created.");
  const slot = $("pilot_download_slot");
  if (result.data.ok && result.data.pilot_package && result.data.pilot_package.archive_file) {
    const pp = result.data.pilot_package;
    const href = pilotDownloadLink(pp.archive_file, pp.pack_id);
    slot.innerHTML = `<a class="download" href="${href}">Download live pilot acceptance pack</a>`;
  } else slot.innerHTML = "";
});


if ($("release_check_btn")) $("release_check_btn").addEventListener("click", () => {
  const checklist = {
    ok: true,
    release_readiness: "operator_check_required",
    required_before_live_use: [
      "Run python scripts/validate_repo.py",
      "Run python scripts/runtime_smoke.py",
      "Run python scripts/deployment_preflight.py",
      "Run python scripts/validate_release_readiness.py",
      "Change CHANGE_ME_OWNER_TOKEN and CHANGE_ME_PIN_PEPPER in settings.json",
      "Start backend with python scripts/start_kiosk_server.py --host 0.0.0.0 --port 8080",
      "Open /api/health from the phone/tablet before first punch"
    ],
    non_claims: ["This checklist is not a legal compliance seal.", "This checklist is not a production deployment claim."]
  };
  show("owner_result", checklist);
  renderOwnerResult(checklist, "Release-readiness checklist loaded. Resolve default-secret warnings before real use."); markOwnerCard("release_result_hint", "Checklist shown. Resolve default-secret warnings before real use.", "warning");
});

if ($("offline_receipts_btn")) $("offline_receipts_btn").addEventListener("click", async () => { if (!validateOwnerTokenPresent()) return; const res = await fetch(`/api/owner/offline/sync_receipts?owner_token=${encodeURIComponent(ownerToken())}`); const data=await res.json(); show("owner_result", data); renderOwnerResult(data, "Offline sync receipts loaded. Review pending-owner-review items before payroll."); markOwnerCard("offline_review_hint", data.ok ? "Offline sync receipts loaded. Pending review remains non-payroll truth." : friendlyError(data), data.ok ? "warning" : "error"); });

setEmployeeFlow("id", "active");
setOwnerFlow("review", "active");
setOfflineFlow("backend", "active");

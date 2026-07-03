let backendOnline = false;
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
  if (runtimeCard) runtimeCard.className = `runtime-card ${kind}`;
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
function setOfflineFlow(stage, state){
  markFlowDoneUntil("offline", ["backend","local","sync","review","decision"], stage || "backend", state || "active");
}

function backendOfflinePayload(message){
  return { ok:false, error:"backend_unreachable", message: message || "Backend not connected. Ask the owner to start the Python server.", next_action:"Owner should run python scripts/start_kiosk_server.py --host 0.0.0.0 --port 8080" };
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
    setBackendConnection("offline", "Backend not connected", "Start the Python server, then reopen this employee link from your phone or tablet.");
    return { ok:false, status:0, data };
  }
}

function show(id, obj){ $(id).textContent = JSON.stringify(obj, null, 2); }
function fmtStatus(value){
  if (!value) return "—";
  return String(value).replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
}
function safeHtml(value){
  return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
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
function updateTodayCard(summary, receipt, lastPunch){
  const hours = $("today_hours_value");
  const status = $("today_status_value");
  const last = $("today_last_punch_value");
  if (!hours || !status || !last) return;
  if (summary) {
    hours.textContent = `${Number(summary.net_work_hours || 0).toFixed(2)} h`;
    status.textContent = fmtStatus(summary.current_status || "ready");
  }
  if (lastPunch && lastPunch.captured_local) {
    last.textContent = new Date(lastPunch.captured_local).toLocaleTimeString([], {hour:"numeric", minute:"2-digit"});
  } else if (receipt && receipt.captured_local) {
    last.textContent = new Date(receipt.captured_local).toLocaleTimeString([], {hour:"numeric", minute:"2-digit"});
  }
}
function renderLocalInputError(message){
  const card = $("employee_receipt");
  const title = card.querySelector(".receipt-title");
  const msg = card.querySelector(".receipt-message");
  const metrics = card.querySelector(".receipt-metrics");
  card.classList.remove("success", "neutral", "warning");
  card.classList.add("error");
  title.textContent = "Action blocked";
  msg.textContent = message;
  metrics.hidden = true;
  const next = $("receipt_next");
  if (next) next.textContent = "Enter Employee ID and PIN, then try again.";
  setEmployeeStrip("error", message);
  setFocusCard("error", "Action blocked", "Employee ID and PIN are required.");
  setInputGuard("error", message);
  setEmployeeFlow("id", "error");
}
function validateEmployeeInputs(payload){
  if (!payload.employee_id && !payload.pin) return "Employee ID and PIN are required.";
  if (!payload.employee_id) return "Employee ID is required.";
  if (!payload.pin) return "PIN is required.";
  return null;
}
function friendlyError(data){
  const raw = data && (data.error || (data.punch_receipt && data.punch_receipt.policy_flags && data.punch_receipt.policy_flags[0]));
  const map = {
    employee_not_found: "Employee ID was not found. Check the ID or ask the owner.",
    invalid_pin: "PIN not accepted. Check your employee ID and PIN.",
    pin_invalid: "PIN not accepted. Check your employee ID and PIN.",
    employee_inactive: "This employee is inactive. Ask the owner to review.",
  };
  return map[raw] || (raw ? String(raw).replaceAll("_", " ") : "This action did not complete. Ask the owner/manager to review.");
}
function setEmployeeStrip(kind, text){
  const strip = $("employee_status_strip");
  if (!strip) return;
  strip.className = `status-strip ${kind}`;
  strip.innerHTML = `<span class="status-dot ${kind}" aria-hidden="true"></span><span>${text}</span>`;
}
function employeePayload(){
  return { employee_id: $("employee_id").value.trim(), pin: $("pin").value.trim() };
}
function resetEmployeeForNextPerson(){
  $("employee_id").value = "";
  $("pin").value = "";
  $("employee_id").focus();
  setInputGuard("success", "Punch recorded. Ready for the next employee.");
}
function rememberEmployeeId(employeeId){
  if (employeeId) sessionStorage.setItem("bbtc_employee_id", employeeId);
}
function restoreEmployeeId(){
  const saved = sessionStorage.getItem("bbtc_employee_id");
  if (saved && $("employee_id") && !$("employee_id").value) $("employee_id").value = saved;
}

function renderOfflineReceipt(item){
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
  if (next) next.textContent = "Do not clear this browser until the pending offline punch is synced or exported.";
  if ($("today_hours_value")) $("today_hours_value").textContent = "Pending";
  if ($("today_status_value")) $("today_status_value").textContent = "Pending Sync";
  if ($("today_last_punch_value")) $("today_last_punch_value").textContent = new Date(item.captured_at_client_utc).toLocaleTimeString([], {hour:"numeric", minute:"2-digit"});
  setFocusCard("warning", "Offline recovery saved", "The punch is stored locally and must be synced/reviewed before payroll use.");
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
    setFocusCard("error", "Punch not recorded", "Review the message, then correct Employee ID/PIN.");
    setEmployeeStrip("error", msg.textContent);
    return;
  }
  if (receipt.accepted) {
    card.classList.add("success");
    title.textContent = `Success — ${receipt.event_label || "Punch accepted"}`;
    rememberEmployeeId(receipt.employee_id);
  } else {
    card.classList.add("error");
    title.textContent = "Punch rejected";
  }
  msg.textContent = receipt.accepted ? (receipt.message || "Punch accepted.") : friendlyError(data);
  if (receipt.today_summary) {
    $("receipt_hours").textContent = `${Number(receipt.today_summary.net_work_hours || 0).toFixed(2)} h`;
    $("receipt_status").textContent = fmtStatus(receipt.today_summary.current_status);
    $("receipt_time").textContent = receipt.captured_local ? new Date(receipt.captured_local).toLocaleTimeString([], {hour:"numeric", minute:"2-digit"}) : "—";
    metrics.hidden = false;
    updateTodayCard(receipt.today_summary, receipt);
    if (next) next.textContent = receipt.accepted ? "You can step away once this success receipt is visible." : "This punch did not enter payroll review until corrected.";
    setFocusCard(receipt.accepted ? "success" : "error", receipt.accepted ? "Punch accepted" : "Punch rejected", receipt.accepted ? `${receipt.event_label || "Punch"} recorded. Today shows ${Number(receipt.today_summary.net_work_hours || 0).toFixed(2)} hours.` : "The punch was rejected. Review the message before retrying.");
    setInputGuard(receipt.accepted ? "success" : "error", receipt.accepted ? "Receipt visible. You may step away after confirming the message." : "Punch rejected. Correct the issue before retrying.");
    setEmployeeStrip(receipt.accepted ? "success" : "error", `${receipt.event_label || "Punch"} · Today: ${Number(receipt.today_summary.net_work_hours || 0).toFixed(2)} h · ${fmtStatus(receipt.today_summary.current_status)}`);
    setEmployeeFlow(receipt.accepted ? "synced" : "receipt", receipt.accepted ? "done" : "error");
  } else {
    metrics.hidden = true;
    setEmployeeStrip("error", msg.textContent);
  }
}

function renderHoursSummary(data){
  const card = $("employee_receipt");
  const title = card.querySelector(".receipt-title");
  const msg = card.querySelector(".receipt-message");
  const metrics = card.querySelector(".receipt-metrics");
  const next = $("receipt_next");
  if (!data || !data.ok || !data.today_summary) {
    card.classList.remove("success", "neutral", "warning");
    card.classList.add("error");
    title.textContent = "Hours not available";
    msg.textContent = friendlyError(data);
    metrics.hidden = true;
    if (next) next.textContent = "Check Employee ID and PIN, then try again.";
    setFocusCard("error", "Hours lookup failed", friendlyError(data));
    setEmployeeStrip("error", friendlyError(data));
    setEmployeeFlow("pin", "error");
    return;
  }
  rememberEmployeeId(data.today_summary.employee_id);
  const summary = data.today_summary;
  card.classList.remove("error", "neutral", "warning");
  card.classList.add("success");
  title.textContent = "Today's hours loaded";
  msg.textContent = `${summary.display_name || summary.employee_id}: ${Number(summary.net_work_hours || 0).toFixed(2)} hours today.`;
  $("receipt_hours").textContent = `${Number(summary.net_work_hours || 0).toFixed(2)} h`;
  $("receipt_status").textContent = fmtStatus(summary.current_status);
  $("receipt_time").textContent = data.last_punch && data.last_punch.captured_local ? new Date(data.last_punch.captured_local).toLocaleTimeString([], {hour:"numeric", minute:"2-digit"}) : "—";
  metrics.hidden = false;
  updateTodayCard(summary, null, data.last_punch);
  if (next) next.textContent = "Choose a punch action when you are ready to clock in or out.";
  setFocusCard("success", "Today's hours", `Status: ${fmtStatus(summary.current_status)} · ${Number(summary.net_work_hours || 0).toFixed(2)} hours today.`);
  setInputGuard("success", "Hours loaded. PIN is not stored in the browser.");
  setEmployeeStrip("success", `Today: ${Number(summary.net_work_hours || 0).toFixed(2)} h · ${fmtStatus(summary.current_status)}`);
  setEmployeeFlow("punch", "active");
}

async function checkBackendHealth(){
  if (location.protocol === "file:") {
    setBackendConnection("offline", "Backend not connected", "This page is open as a file preview. Use the employee link or QR from the owner console.");
    return;
  }
  try {
    const res = await fetch("/api/health", { cache:"no-store" });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error("health check failed");
    const warnings = data.setup_warnings && data.setup_warnings.length ? ` Setup warnings: ${data.setup_warnings.join(", ")}` : "";
    setBackendConnection(warnings ? "warning" : "online", `Runtime v${data.version} online`, `Backend is connected. Employee punches can be recorded.${warnings}`);
  } catch (err) {
    setBackendConnection("offline", "Backend not connected", "Ask the owner to start the Python server, then reopen this employee link.");
  }
}

function updateOfflineUi(){
  if (!window.OfflineTimekeeper) return;
  const st = window.OfflineTimekeeper.status();
  const badge = $("offline_queue_badge");
  const status = $("offline_queue_status");
  if (badge) badge.textContent = `${st.pending_count} pending`;
  if (status) status.textContent = st.pending_count ? `Offline queue has ${st.pending_count} pending recovery item(s) on this device.` : "No pending offline punches on this device.";
}

document.querySelectorAll("button[data-event]").forEach(btn => btn.addEventListener("click", async () => {
  const payload = { ...employeePayload(), event_type: btn.dataset.event, source: "employee_portal" };
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
    show("clock_result", { ok:false, offline_saved:true, offline_item:offlineItem });
  } else {
    renderPunchReceipt(result.data);
    show("clock_result", result.data);
    if (result.data && result.data.punch_receipt && result.data.punch_receipt.accepted) {
      resetEmployeeForNextPerson();
    }
  }
  btn.disabled = false;
}));

if ($("view_hours_btn")) $("view_hours_btn").addEventListener("click", async () => {
  const payload = employeePayload();
  const inputError = validateEmployeeInputs(payload);
  if (inputError) { renderLocalInputError(inputError); show("clock_result", {ok:false, local_validation:"blocked", error:inputError}); return; }
  setEmployeeFlow("pin", "pending");
  setInputGuard("pending", "Loading today's hours…");
  const result = await postJson("/api/employee/summary", payload);
  renderHoursSummary(result.data);
  show("clock_result", result.data);
});

if ($("guest_sign_in_btn")) $("guest_sign_in_btn").addEventListener("click", async () => {
  const guestName = $("guest_name").value.trim();
  if (!guestName) {
    $("guest_result").className = "owner-card-result error";
    $("guest_result").textContent = "Guest name is required.";
    $("guest_name").focus();
    return;
  }
  const result = await postJson("/api/guests/sign-in", {
    guest_name:guestName,
    organization:$("guest_organization").value.trim(),
    purpose:$("guest_purpose").value.trim(),
    notes:$("guest_notes").value.trim()
  });
  if (result.data && result.data.ok) {
    $("guest_result").className = "owner-card-result success";
    $("guest_result").textContent = `${guestName} signed in. This kiosk is ready for the next person.`;
    ["guest_name","guest_organization","guest_purpose","guest_notes"].forEach(id => $(id).value = "");
    $("guest_name").focus();
    await loadActiveGuests();
  } else {
    $("guest_result").className = "owner-card-result error";
    $("guest_result").textContent = result.data && result.data.error ? fmtStatus(result.data.error) : "Guest sign-in failed.";
  }
});

function renderActiveGuests(guests){
  const target = $("active_guest_list");
  if (!target) return;
  if ($("active_guest_count")) $("active_guest_count").textContent = `${guests.length} onsite`;
  if (!guests.length) {
    target.innerHTML = '<div class="empty-manager-state">No visitors are currently signed in.</div>';
    return;
  }
  target.innerHTML = guests.map(guest => `
    <article class="active-visitor-card">
      <div>
        <strong>${safeHtml(guest.display_name)}</strong>
        <small>${safeHtml(guest.organization || guest.purpose || "Guest visitor")} · Signed in ${new Date(guest.signed_in_at_local).toLocaleTimeString([], {hour:"numeric", minute:"2-digit"})}</small>
      </div>
      <button type="button" class="secondary-action guest-row-sign-out" data-guest-session-id="${safeHtml(guest.guest_session_id)}">Sign Out</button>
    </article>`).join("");
  target.querySelectorAll(".guest-row-sign-out").forEach(button => button.addEventListener("click", async () => {
    button.disabled = true;
    const result = await postJson("/api/guests/sign-out", {guest_session_id:button.dataset.guestSessionId});
    if (result.data && result.data.ok) {
      $("guest_result").className = "owner-card-result success";
      $("guest_result").textContent = `${result.data.guest_session.guest_name} signed out. The kiosk is ready for the next person.`;
      await loadActiveGuests();
    } else {
      button.disabled = false;
      $("guest_result").className = "owner-card-result error";
      $("guest_result").textContent = result.data && result.data.error ? fmtStatus(result.data.error) : "Guest sign-out failed.";
    }
  }));
}

async function loadActiveGuests(){
  const target = $("active_guest_list");
  if (!target) return;
  try {
    const res = await fetch("/api/guests/active", {cache:"no-store"});
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || "active_guests_unavailable");
    renderActiveGuests(data.active_guest_sessions || []);
  } catch {
    target.innerHTML = '<div class="empty-manager-state">Active visitors are unavailable while the backend is disconnected.</div>';
  }
}

if (window.OfflineTimekeeper) {
  updateOfflineUi();
  window.addEventListener("offline-queue-change", updateOfflineUi);
  if ($("sync_offline_btn")) $("sync_offline_btn").addEventListener("click", async () => {
    try { const data = await window.OfflineTimekeeper.syncPending(); show("clock_result", data); setEmployeeStrip("success", "Offline queue sync completed. Items remain pending owner review."); }
    catch (err) { show("clock_result", {ok:false, error:String(err.message || err)}); setEmployeeStrip("error", "Offline sync failed."); }
    updateOfflineUi();
  });
  if ($("download_offline_jsonl_btn")) $("download_offline_jsonl_btn").addEventListener("click", () => window.OfflineTimekeeper.downloadPendingJsonl());
  if ($("download_offline_csv_btn")) $("download_offline_csv_btn").addEventListener("click", () => window.OfflineTimekeeper.downloadPendingCsv());
  if ($("clear_synced_offline_btn")) $("clear_synced_offline_btn").addEventListener("click", () => { window.OfflineTimekeeper.clearSynced(); updateOfflineUi(); });
}

restoreEmployeeId();
checkBackendHealth();
loadActiveGuests();
setInterval(checkBackendHealth, 30000);
setInterval(loadActiveGuests, 15000);
setEmployeeFlow("id", "active");
setOfflineFlow("backend", "active");

if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  document.documentElement.classList.add("reduce-motion");
}

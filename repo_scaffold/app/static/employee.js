let backendOnline = false;
let kioskSocket = null;
let kioskSocketPort = null;
let resetTimer = null;
const $ = (id) => document.getElementById(id);

function localClockParts(){
  const now = new Date();
  const parts = new Intl.DateTimeFormat([], {hour:"numeric", minute:"2-digit", second:"2-digit", hour12:true}).formatToParts(now);
  const value = type => parts.find(part => part.type === type)?.value || "";
  return {
    iso: now.toISOString(),
    hourMinute: `${value("hour")}:${value("minute")}`,
    seconds: `:${value("second")}`,
    period: value("dayPeriod"),
    day: now.toLocaleDateString([], {weekday:"long", month:"long", day:"numeric", year:"numeric"})
  };
}

function tickClock(){
  const parts = localClockParts();
  $("current_time").dateTime = parts.iso;
  $("clock_hm").textContent = parts.hourMinute;
  $("clock_seconds").textContent = parts.seconds;
  $("clock_period").textContent = parts.period;
  $("business_day").textContent = parts.day;
}

function setConnection(kind, title, detail){
  backendOnline = kind === "online" || kind === "warning";
  const banner = $("backend_connection_banner");
  banner.className = `kiosk-connection-message ${kind}`;
  $("backend_connection_title").textContent = title;
  $("backend_connection_detail").textContent = detail;
}

function setLiveState(kind, title, detail){
  const target = $("kiosk_live_status");
  target.className = `kiosk-live-status ${kind}`;
  target.querySelector("strong").textContent = title;
  target.querySelector("small").textContent = detail;
}

function applyKioskStatus(data){
  if (!data) return;
  $("kiosk_employee_count").textContent = String(data.active_employee_count ?? 0);
  $("kiosk_visitor_count").textContent = String(data.active_guest_count ?? 0);
}

async function loadKioskStatus(){
  try {
    const res = await fetch("/api/kiosk/status", {cache:"no-store"});
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error("status_unavailable");
    applyKioskStatus(data);
  } catch {
    setLiveState("fallback", "Reconnecting", "Counts may be delayed");
  }
}

function connectKioskLive(){
  if (!kioskSocketPort || !window.WebSocket) {
    setLiveState("fallback", "Polling", "Updates every 15 seconds");
    return;
  }
  if (kioskSocket && kioskSocket.readyState <= WebSocket.OPEN) return;
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${scheme}://${location.hostname}:${kioskSocketPort}/kiosk/live`);
  kioskSocket = socket;
  socket.addEventListener("open", () => setLiveState("live", "Live connection", "Anonymous counts only"));
  socket.addEventListener("message", event => {
    try {
      const data = JSON.parse(event.data);
      if (data.message_type === "kiosk_status") {
        applyKioskStatus(data);
        setLiveState("live", "Live connection", "Anonymous counts only");
      }
    } catch {}
  });
  socket.addEventListener("close", () => {
    if (kioskSocket === socket) kioskSocket = null;
    setLiveState("fallback", "Polling", "Reconnecting live status");
  });
  socket.addEventListener("error", () => setLiveState("fallback", "Polling", "Live connection unavailable"));
}

async function checkBackendHealth(){
  if (location.protocol === "file:") {
    setConnection("offline", "Time clock unavailable", "Open the kiosk link supplied by the operator.");
    return;
  }
  try {
    const res = await fetch("/api/health", {cache:"no-store"});
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error("health_failed");
    kioskSocketPort = data.websocket && data.websocket.available ? data.websocket.port : null;
    setConnection("online", "Time clock ready", "Employee and visitor actions are available.");
    connectKioskLive();
  } catch {
    kioskSocketPort = null;
    setConnection("offline", "Time clock unavailable", "Please ask a manager for help. No action can be recorded right now.");
    setLiveState("offline", "Offline", "Ask a manager for help");
  }
}

function selectMode(mode){
  const employee = mode === "employee";
  $("employee_mode_btn").classList.toggle("active", employee);
  $("employee_mode_btn").setAttribute("aria-selected", String(employee));
  $("visitor_mode_btn").classList.toggle("active", !employee);
  $("visitor_mode_btn").setAttribute("aria-selected", String(!employee));
  $("employee_mode_panel").hidden = !employee;
  $("visitor_mode_panel").hidden = employee;
  window.clearTimeout(resetTimer);
  if (employee) $("employee_id").focus();
  else $("guest_name").focus();
}

function clearPrivateFields(){
  ["employee_id","pin","guest_name","guest_organization","guest_purpose","guest_notes"].forEach(id => {
    const input = $(id);
    if (input) input.value = "";
  });
}

function scheduleReadyReset(){
  window.clearTimeout(resetTimer);
  resetTimer = window.setTimeout(() => {
    clearPrivateFields();
    selectMode("employee");
    setReceipt("neutral", "Ready for the next person", "Choose a mode and complete your action.");
    $("employee_input_guard").textContent = "Both fields are required. Nothing is remembered on this kiosk.";
  }, 7000);
}

function setReceipt(kind, title, message){
  const receipt = $("kiosk_receipt");
  receipt.className = `kiosk-receipt ${kind}`;
  receipt.querySelector(".receipt-symbol").textContent = kind === "error" ? "!" : kind === "pending" ? "…" : "✓";
  $("kiosk_receipt_title").textContent = title;
  $("kiosk_receipt_message").textContent = message;
  $("kiosk_receipt_time").textContent = new Date().toLocaleTimeString([], {hour:"numeric", minute:"2-digit"});
}

function friendlyError(data){
  const raw = data && (data.error || data.punch_receipt?.policy_flags?.[0]);
  const messages = {
    employee_not_found: "Employee ID was not found. Check the ID or ask a manager.",
    invalid_pin: "PIN not accepted. Check your ID and PIN.",
    pin_invalid: "PIN not accepted. Check your ID and PIN.",
    employee_inactive: "This employee is inactive. Please ask a manager.",
    guest_name_required: "Enter your full name.",
    active_guest_not_found: "No active visit matched that name. Check the spelling or ask a manager.",
    guest_name_ambiguous_add_organization: "More than one active visit uses that name. Add your organization or ask a manager."
  };
  return messages[raw] || "The action did not complete. Please check the information or ask a manager.";
}

async function postJson(url, payload){
  try {
    const res = await fetch(url, {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(payload)
    });
    const data = await res.json();
    return {ok:res.ok && Boolean(data.ok), status:res.status, data};
  } catch {
    return {ok:false, status:0, data:{error:"backend_unreachable"}};
  }
}

function employeePayload(eventType){
  return {
    employee_id:$("employee_id").value.trim(),
    pin:$("pin").value.trim(),
    event_type:eventType,
    source:"shared_timeclock_kiosk"
  };
}

function actionLabel(eventType){
  return {
    clock_in:"Clock in",
    clock_out:"Clock out",
    break_start:"Break started",
    break_end:"Break ended"
  }[eventType] || "Time clock action";
}

document.querySelectorAll("[data-event]").forEach(button => button.addEventListener("click", async () => {
  const payload = employeePayload(button.dataset.event);
  if (!payload.employee_id || !payload.pin) {
    setReceipt("error", "Information required", "Enter both Employee ID and PIN.");
    $("employee_input_guard").textContent = "Employee ID and PIN are both required.";
    (!payload.employee_id ? $("employee_id") : $("pin")).focus();
    return;
  }
  if (!backendOnline) {
    clearPrivateFields();
    setReceipt("error", "Action not recorded", "The time clock is offline. Please ask a manager for help.");
    scheduleReadyReset();
    return;
  }
  button.disabled = true;
  setReceipt("pending", "Recording action", "Please wait. Do not tap again.");
  const result = await postJson("/api/clock", payload);
  clearPrivateFields();
  if (result.ok && result.data?.punch_receipt?.accepted) {
    setReceipt("success", `${actionLabel(payload.event_type)} successful`, "Your action was recorded. You may step away.");
    await loadKioskStatus();
  } else {
    setReceipt("error", "Action not recorded", result.status === 0 ? "The time clock lost connection. Please ask a manager." : friendlyError(result.data));
  }
  button.disabled = false;
  scheduleReadyReset();
}));

async function runGuestAction(action){
  const guestName = $("guest_name").value.trim();
  if (!guestName) {
    setReceipt("error", "Name required", "Enter your full name before continuing.");
    $("guest_name").focus();
    return;
  }
  if (!backendOnline) {
    clearPrivateFields();
    setReceipt("error", "Action not recorded", "The time clock is offline. Please ask a manager for help.");
    scheduleReadyReset();
    return;
  }
  const url = action === "in" ? "/api/guests/sign-in" : "/api/guests/sign-out";
  const payload = action === "in" ? {
    guest_name:guestName,
    organization:$("guest_organization").value.trim(),
    purpose:$("guest_purpose").value.trim(),
    notes:$("guest_notes").value.trim()
  } : {
    guest_name:guestName,
    organization:$("guest_organization").value.trim()
  };
  const buttons = [$("guest_sign_in_btn"), $("guest_sign_out_btn")];
  buttons.forEach(button => button.disabled = true);
  setReceipt("pending", action === "in" ? "Signing in" : "Signing out", "Please wait. Do not tap again.");
  const result = await postJson(url, payload);
  clearPrivateFields();
  if (result.ok) {
    setReceipt("success", action === "in" ? "Visitor sign-in successful" : "Visitor sign-out successful", "Your visit record was updated. You may step away.");
    await loadKioskStatus();
  } else {
    setReceipt("error", "Visitor action not recorded", result.status === 0 ? "The time clock lost connection. Please ask a manager." : friendlyError(result.data));
  }
  buttons.forEach(button => button.disabled = false);
  scheduleReadyReset();
}

$("employee_mode_btn").addEventListener("click", () => selectMode("employee"));
$("visitor_mode_btn").addEventListener("click", () => selectMode("visitor"));
$("guest_sign_in_btn").addEventListener("click", () => runGuestAction("in"));
$("guest_sign_out_btn").addEventListener("click", () => runGuestAction("out"));

tickClock();
setInterval(tickClock, 1000);
checkBackendHealth();
loadKioskStatus();
setInterval(checkBackendHealth, 30000);
setInterval(loadKioskStatus, 15000);
setInterval(connectKioskLive, 5000);

if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  document.documentElement.classList.add("reduce-motion");
}

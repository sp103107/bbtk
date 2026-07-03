(function(){
  const KEY = "bbtc_offline_punch_queue_v1";
  const DEVICE_KEY = "bbtc_offline_device_id_v1";
  function uuid(){ return (crypto && crypto.randomUUID) ? crypto.randomUUID() : `local_${Date.now()}_${Math.random().toString(16).slice(2)}`; }
  function deviceId(){
    let v = localStorage.getItem(DEVICE_KEY);
    if (!v) { v = `browser_kiosk_${uuid().replaceAll('-', '').slice(0,12)}`; localStorage.setItem(DEVICE_KEY, v); }
    return v;
  }
  function readQueue(){
    try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
  }
  function writeQueue(items){ localStorage.setItem(KEY, JSON.stringify(items)); window.dispatchEvent(new CustomEvent("offline-queue-change")); }
  function pending(){ return readQueue().filter(x => x.sync_status !== "synced"); }
  function savePunchIntent(payload){
    const item = {
      offline_event_id: `offline_${Date.now()}_${uuid().slice(0,8)}`,
      employee_id: String(payload.employee_id || "").trim(),
      event_type: String(payload.event_type || "").trim(),
      captured_at_client_utc: new Date().toISOString(),
      captured_local_display: new Date().toLocaleString(),
      local_device_id: deviceId(),
      source: "browser_offline_queue",
      sync_status: "pending",
      pin_persisted: false,
      pin_policy: "PIN was not persisted. Offline item is recovery evidence pending owner review."
    };
    const q = readQueue(); q.push(item); writeQueue(q); return item;
  }
  function toJsonl(items){ return items.map(x => JSON.stringify(x)).join("\n") + (items.length ? "\n" : ""); }
  function csvEscape(v){ const s=String(v ?? ""); return /[",\n]/.test(s) ? `"${s.replaceAll('"','""')}"` : s; }
  function toCsv(items){
    const fields=["offline_event_id","employee_id","event_type","captured_at_client_utc","captured_local_display","local_device_id","sync_status","pin_persisted"];
    return [fields.join(",")].concat(items.map(x => fields.map(f => csvEscape(x[f])).join(","))).join("\n") + "\n";
  }
  function download(name, text, type){
    const blob = new Blob([text], {type}); const url = URL.createObjectURL(blob); const a=document.createElement("a");
    a.href=url; a.download=name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url), 1000);
  }
  async function syncPending(){
    const q = readQueue(); const items = q.filter(x => x.sync_status !== "synced");
    if (!items.length) return {ok:true, sync_status:"nothing_pending", pending_review_count:0, rejected_count:0};
    const batch = { offline_batch_id:`offline_batch_${Date.now()}_${uuid().slice(0,8)}`, terminal_id: deviceId(), created_at_client_utc: new Date().toISOString(), items };
    const res = await fetch("/api/offline/sync", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(batch)});
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || "offline_sync_failed");
    const acceptedIds = new Set((data.pending_review_items || []).map(x => x.offline_event_id));
    const next = q.map(x => acceptedIds.has(x.offline_event_id) ? {...x, sync_status:"synced", sync_receipt_file:data.receipt_file || null, canonical_status:"pending_owner_review"} : x);
    writeQueue(next); return data;
  }
  function clearSynced(){ writeQueue(readQueue().filter(x => x.sync_status !== "synced")); }
  window.OfflineTimekeeper = {
    deviceId, readQueue, pending, savePunchIntent, syncPending, clearSynced,
    downloadPendingJsonl: () => download(`best_buds_offline_pending_${Date.now()}.jsonl`, toJsonl(pending()), "application/x-ndjson"),
    downloadPendingCsv: () => download(`best_buds_offline_pending_${Date.now()}.csv`, toCsv(pending()), "text/csv"),
    status: () => ({device_id:deviceId(), pending_count:pending().length, total_count:readQueue().length})
  };
})();

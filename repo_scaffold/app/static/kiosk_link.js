const kioskEl = (id) => document.getElementById(id);

function markKioskHint(text, kind="success"){
  const el = kioskEl("kiosk_link_result_hint");
  if (!el) return;
  el.className = `owner-card-result ${kind}`;
  el.textContent = text;
}

function pickPreferredKioskUrl(urls){
  if (!urls || !urls.length) return `${location.protocol}//${location.host}/employee`;
  const lan = urls.find(u => !u.includes("127.0.0.1") && !u.includes("localhost"));
  return lan || urls[0];
}

function renderQr(target, url){
  if (!target) return;
  target.innerHTML = "";
  const img = document.createElement("img");
  img.alt = "Shared time clock kiosk QR code";
  img.width = 180;
  img.height = 180;
  img.src = `/api/kiosk/qr.svg?url=${encodeURIComponent(url)}`;
  target.appendChild(img);
}

async function loadKioskLinkCard(announce=false){
  const linkEl = kioskEl("kiosk_employee_url");
  const qrEl = kioskEl("kiosk_qr_target");
  const hintEl = kioskEl("kiosk_link_hint");
  if (!linkEl) return;
  try {
    const res = await fetch("/api/config/kiosk_urls", { cache: "no-store" });
    const data = await res.json();
    const url = pickPreferredKioskUrl(data.urls || []);
    linkEl.textContent = url;
    linkEl.href = url;
    renderQr(qrEl, url);
    if (hintEl) hintEl.textContent = "Open this QR on the shared tablet for privacy-safe employee and visitor actions.";
    if (announce) markKioskHint("Fresh shared-kiosk QR generated.", "success");
  } catch (err) {
    const fallback = `${location.origin}/employee`;
    linkEl.textContent = fallback;
    linkEl.href = fallback;
    renderQr(qrEl, fallback);
    if (hintEl) hintEl.textContent = "Could not load LAN URLs automatically. Use the link shown for this browser session.";
    if (announce) markKioskHint("QR generated with this browser's fallback address.", "warning");
  }
}

if (kioskEl("generate_kiosk_qr_btn")) kioskEl("generate_kiosk_qr_btn").addEventListener("click", async () => {
  const button = kioskEl("generate_kiosk_qr_btn");
  button.disabled = true;
  button.textContent = "Generating…";
  await loadKioskLinkCard(true);
  button.disabled = false;
  button.textContent = "Generate Kiosk QR";
});

if (kioskEl("copy_kiosk_link_btn")) kioskEl("copy_kiosk_link_btn").addEventListener("click", async () => {
  const link = kioskEl("kiosk_employee_url");
  if (!link) return;
  try {
    await navigator.clipboard.writeText(link.textContent || link.href);
    markKioskHint("Shared kiosk link copied.", "success");
  } catch (err) {
    markKioskHint("Copy failed. Select the link manually.", "error");
  }
});

if (kioskEl("open_kiosk_link_btn")) kioskEl("open_kiosk_link_btn").addEventListener("click", () => {
  const link = kioskEl("kiosk_employee_url");
  if (link && link.href) window.open(link.href, "_blank", "noopener");
});

if (kioskEl("print_kiosk_poster_btn")) kioskEl("print_kiosk_poster_btn").addEventListener("click", () => {
  const link = kioskEl("kiosk_employee_url");
  if (!link || !link.href) {
    markKioskHint("Generate the shared kiosk link before printing.", "warning");
    return;
  }
  const includeNotice = kioskEl("poster_notice_enabled")?.checked !== false;
  const posterUrl = `/kiosk-poster?url=${encodeURIComponent(link.href)}&notice=${includeNotice ? "1" : "0"}`;
  window.open(posterUrl, "_blank", "noopener");
  markKioskHint(`Print-ready kiosk poster opened ${includeNotice ? "with" : "without"} the authorized-access notice.`, "success");
});

loadKioskLinkCard();

const posterQr = document.getElementById("poster_qr");
const posterUrl = document.getElementById("poster_url");
const printButton = document.getElementById("print_poster_btn");

function safeKioskUrl(candidate) {
  try {
    const parsed = new URL(candidate, window.location.origin);
    if (!["http:", "https:"].includes(parsed.protocol)) return null;
    return parsed.href;
  } catch {
    return null;
  }
}

function renderPoster(url) {
  const kioskUrl = safeKioskUrl(url) || `${window.location.origin}/employee`;
  posterQr.src = `/api/kiosk/qr.svg?url=${encodeURIComponent(kioskUrl)}`;
  posterUrl.href = kioskUrl;
  posterUrl.textContent = kioskUrl;
}

async function initializePoster() {
  const parameters = new URLSearchParams(window.location.search);
  const requestedUrl = parameters.get("url");
  const accessNotice = document.getElementById("poster_access_notice");
  if (accessNotice) accessNotice.hidden = parameters.get("notice") === "0";
  if (safeKioskUrl(requestedUrl)) {
    renderPoster(requestedUrl);
    return;
  }
  try {
    const response = await fetch("/api/config/kiosk_urls", { cache: "no-store" });
    const data = await response.json();
    const urls = Array.isArray(data.urls) ? data.urls : [];
    const lanUrl = urls.find(url => !url.includes("127.0.0.1") && !url.includes("localhost"));
    renderPoster(lanUrl || urls[0]);
  } catch {
    renderPoster(`${window.location.origin}/employee`);
  }
}

if (printButton) printButton.addEventListener("click", () => window.print());
initializePoster();

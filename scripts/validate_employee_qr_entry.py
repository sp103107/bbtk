#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
PHASE = "rc7_6_employee_qr_entry_and_kiosk_fit"
errors: list[str] = []
checks: dict[str, bool] = {}
REQUIRED = [
    "repo_scaffold/app/static/employee.html",
    "repo_scaffold/app/static/employee.js",
    "repo_scaffold/app/static/kiosk_link.js",
    "contracts/ui_ux/employee_qr_entry_contract.v0.8.6.json",
    "contracts/frontend_surface/employee_portal_surface.v0.8.6.json",
    "docs/EMPLOYEE_QR_ENTRY_PORTAL_v0.8.6.md",
    "docs/QR_URL_CLOCK_FLOW.md",
    "release_candidate/rc7_6_employee_qr_entry_and_kiosk_fit/README.md",
    "frontend/save_state/employee_qr_entry_save_state.v0.8.6.json",
    "scripts/start_all.bat",
    "scripts/start_all.sh",
]
for rel in REQUIRED:
    ok = (ROOT / rel).exists()
    checks[f"present:{rel}"] = ok
    if not ok:
        errors.append(f"missing:{rel}")
server = (ROOT / "repo_scaffold/app/server.py").read_text(encoding="utf-8")
html = (ROOT / "repo_scaffold/app/static/employee.html").read_text(encoding="utf-8")
index = (ROOT / "repo_scaffold/app/static/index.html").read_text(encoding="utf-8")
emp_js = (ROOT / "repo_scaffold/app/static/employee.js").read_text(encoding="utf-8")
kiosk_js = (ROOT / "repo_scaffold/app/static/kiosk_link.js").read_text(encoding="utf-8")
css = (ROOT / "repo_scaffold/app/static/style.css").read_text(encoding="utf-8")
route_checks = {
    "employee_route": 'parsed.path == "/employee"' in server,
    "employee_summary_api": 'parsed.path == "/api/employee/summary"' in server,
    "kiosk_urls_api": 'parsed.path == "/api/config/kiosk_urls"' in server,
    "qr_svg_api": 'parsed.path == "/api/kiosk/qr.svg"' in server,
    "offline_queue_static": '"/static/offline_queue.js"' in server,
    "employee_static": '"/static/employee.js"' in server,
    "app_version_current": f'APP_VERSION = "{VERSION}"' in server,
    "employee_portal_markup": "timeclock-kiosk" in html and "employee_mode_panel" in html and "visitor_mode_panel" in html,
    "employee_summary_client": "/api/employee/summary" not in emp_js and "individual hours" in html,
    "employee_clock_source": 'source:"shared_timeclock_kiosk"' in emp_js,
    "owner_kiosk_link_card": "kiosk_employee_url" in index and "kiosk_qr_target" in index,
    "qr_render_client": "/api/kiosk/qr.svg" in kiosk_js,
    "mobile_css_present": ".kiosk-shell" in css and "reduce-motion" in css,
    "no_hosted_deployment_claim": "hosted deployment completed" not in index.lower(),
}
for k, v in route_checks.items():
    checks[k] = bool(v)
    if not v:
        errors.append(k)
report = {
    "version": VERSION,
    "phase": PHASE,
    "status": "pass" if not errors else "fail",
    "checks": checks,
    "errors": errors,
    "non_claims": [
        "static and route validation only",
        "no visual regression execution",
        "QR proves URL reachability only",
        "no production deployment claim",
    ],
}
out = ROOT / f"validation/employee_qr_entry_validation_report.v{VERSION}.json"
out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2, sort_keys=True))
sys.exit(0 if report["status"] == "pass" else 1)

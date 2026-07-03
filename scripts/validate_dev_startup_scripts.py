#!/usr/bin/env python3
"""Validate local dev start-all scripts."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
errors: list[str] = []
checks: dict[str, bool] = {}
for rel in ["scripts/start_all.bat", "scripts/start_all.sh"]:
    ok = (ROOT / rel).exists()
    checks[f"present:{rel}"] = ok
    if not ok:
        errors.append(f"missing:{rel}")
bat = (ROOT / "scripts/start_all.bat").read_text(encoding="utf-8")
sh = (ROOT / "scripts/start_all.sh").read_text(encoding="utf-8")
checks["bat_starts_kiosk_server"] = "start_kiosk_server.py" in bat and "/employee" in bat
checks["sh_starts_kiosk_server"] = "start_kiosk_server.py" in sh and "/employee" in sh
checks["bat_health_wait"] = "/api/health" in bat
checks["sh_health_wait"] = "/api/health" in sh
checks["non_claim_present"] = "production deployment" in bat.lower() and "production deployment" in sh.lower()
for key in ["bat_starts_kiosk_server", "sh_starts_kiosk_server", "bat_health_wait", "sh_health_wait", "non_claim_present"]:
    if not checks[key]:
        errors.append(key)
res = subprocess.run(["bash", "-n", "scripts/start_all.sh"], cwd=ROOT, capture_output=True, text=True)
checks["shell_syntax"] = res.returncode == 0
if res.returncode:
    errors.append(f"shell_syntax:{res.stderr.strip()}")
report = {
    "version": VERSION,
    "phase": "rc7_6_employee_qr_entry_and_kiosk_fit",
    "status": "pass" if not errors else "fail",
    "checks": checks,
    "errors": errors,
    "non_claims": ["local dev startup validation only", "no deployment claim"],
}
out = ROOT / f"validation/dev_startup_scripts_validation_report.v{VERSION}.json"
out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2, sort_keys=True))
sys.exit(0 if report["status"] == "pass" else 1)

#!/usr/bin/env python3
from __future__ import annotations
import json, datetime as dt, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/"VERSION").read_text().strip()
REPORT=ROOT/f"validation/offline_timekeeper_validation_report.v{VERSION}.json"
APP_JS=(ROOT/"repo_scaffold/app/static/app.js").read_text(encoding="utf-8")
OFFLINE_JS=(ROOT/"repo_scaffold/app/static/offline_queue.js").read_text(encoding="utf-8")
SERVER=(ROOT/"repo_scaffold/app/server.py").read_text(encoding="utf-8")
checks={
  "offline_queue_script_present": "OfflineTimekeeper" in OFFLINE_JS,
  "pin_not_persisted_claim_present": "pin_persisted: false" in OFFLINE_JS and "PIN was not persisted" in OFFLINE_JS,
  "employee_handler_saves_offline_on_backend_interrupt": "savePunchIntent" in APP_JS and "result.status === 0" in APP_JS,
  "sync_endpoint_present": '"/api/offline/sync"' in SERVER,
  "pending_owner_review_status_present": "offline_recovery_pending_owner_review" in SERVER,
  "csv_mirror_present": "append_csv_ledger_mirror" in SERVER,
  "offline_ui_controls_present": "sync_offline_btn" in (ROOT/"repo_scaffold/app/static/index.html").read_text(encoding="utf-8"),
}
status="pass" if all(checks.values()) else "fail"
report={"checked_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"version":VERSION,"status":status,"checks":checks,"non_claims":["Offline queue is recovery evidence only.","Employee PINs must not be persisted in browser storage.","Offline synced events require owner review before payroll counting."]}
REPORT.parent.mkdir(parents=True, exist_ok=True); REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if status=="pass" else 1)

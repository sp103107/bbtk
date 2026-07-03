#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, shutil, tempfile, datetime as dt, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"repo_scaffold/app"
VERSION=(ROOT/"VERSION").read_text().strip()
REPORT=ROOT/f"validation/csv_ledger_mirror_validation_report.v{VERSION}.json"
def load_server(path):
  spec=importlib.util.spec_from_file_location("bbtc_csv_validate_server", path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
checks={}; errors=[]
with tempfile.TemporaryDirectory(prefix="bbtc_csv_mirror_") as td:
  tmp=Path(td)/"app"; shutil.copytree(APP,tmp); mod=load_server(tmp/"server.py")
  try:
    mod.init_db(); ev=mod.record("emp_001","1234","clock_in","csv_mirror_validation")
    files=list((mod.DATA_DIR/"csv_ledger"/"clock_events").glob("**/*.csv"))
    checks["csv_file_created"]=bool(files)
    text=files[0].read_text(encoding="utf-8") if files else ""
    checks["csv_has_header"]=text.startswith("event_id,employee_id")
    checks["csv_has_event_hash"]=ev["event_hash"] in text
    checks["jsonl_remains_canonical"]=bool(list(mod.LEDGER_DIR.glob("**/*.jsonl")))
  except Exception as e: errors.append(str(e))
status="pass" if not errors and all(checks.values()) else "fail"
report={"checked_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"version":VERSION,"status":status,"checks":checks,"errors":errors,"non_claims":["CSV mirror is not source-of-truth.","JSONL remains canonical."]}
REPORT.parent.mkdir(parents=True, exist_ok=True); REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n", encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True)); sys.exit(0 if status=="pass" else 1)

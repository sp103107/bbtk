#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, shutil, tempfile, datetime as dt, sys, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"repo_scaffold/app"
VERSION=(ROOT/"VERSION").read_text().strip()
REPORT=ROOT/f"reports/runtime_smoke_report.v{VERSION}.json"

def load_server(server_path: Path):
    spec=importlib.util.spec_from_file_location("bbtc_smoke_server", server_path)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def main() -> int:
    errors=[]; checks={}
    with tempfile.TemporaryDirectory(prefix="bbtc_smoke_v081_") as td:
        tmp=Path(td)/"app"; shutil.copytree(APP,tmp)
        shutil.rmtree(tmp/"data", ignore_errors=True)
        mod=load_server(tmp/"server.py")
        try:
            mod.init_db(); checks["init_db"]=True
            ev1=mod.record("emp_001","1234","clock_in","smoke")
            ev2=mod.record("emp_001","1234","break_start","smoke")
            ev3=mod.record("emp_001","1234","break_end","smoke")
            ev4=mod.record("emp_001","1234","clock_out","smoke")
            checks["clock_sequence_accepted"]=all(e["validation_status"]=="accepted" for e in [ev1,ev2,ev3,ev4])
            receipt=mod.punch_receipt(ev4)
            day=mod.employee_day_summary("emp_001")
            checks["employee_success_receipt"]=receipt.get("accepted") is True and "Today total" in receipt.get("message", "")
            checks["employee_today_hours_visible_payload"]=day.get("net_work_hours", -1) >= 0 and day.get("current_status") in {"clocked_out", "clocked_in", "on_break"}
            bad=mod.record("emp_001","0000","clock_in","smoke")
            checks["bad_pin_rejected"]=bad["validation_status"]=="rejected"
            rows=mod.calc(mod.read_events())
            checks["summary_generated"]=bool(rows and rows[0]["source_event_count"]>=4)
            p=mod.export("csv")
            checks["csv_export_created"]=p.exists() and p.suffix==".csv"
            csv_files=list((mod.DATA_DIR/"csv_ledger"/"clock_events").glob("**/*.csv"))
            checks["csv_ledger_mirror_created"]=bool(csv_files) and "event_id" in csv_files[0].read_text(encoding="utf-8")
            offline=mod.sync_offline_batch({"offline_batch_id":"smoke_offline_batch_001","terminal_id":"smoke_phone_01","items":[{"offline_event_id":"local_001","employee_id":"emp_001","event_type":"clock_in","captured_at_client_utc":"2026-06-08T12:00:00+00:00"}]})
            checks["offline_sync_pending_review"]=offline.get("ok") is True and offline.get("pending_review_count")==1 and offline.get("sync_status")=="accepted_pending_owner_review"
            checks["offline_sync_receipt_written"]=bool(mod.list_offline_sync_receipts())
            emp=mod.upsert_employee("emp_002","Smoke Employee","2222")
            checks["employee_upsert"]=emp["employee_id"]=="emp_002"
            adj=mod.create_owner_adjustment("emp_001", "clock_in", "2026-06-08T12:00:00+00:00", "smoke missed punch correction", "smoke owner note")
            checks["owner_adjustment_created"] = adj["event"]["admin_adjustment"] is True
            review=mod.owner_review_report(None, None)
            checks["manager_review_generated"] = review["owner_adjustment_count"] >= 1 and "owner_adjustments_present" in review["review_flags"]
            pp=mod.close_pay_period(None, None, "smoke close")
            ppdir=Path(pp["manifest_path"]).parent
            required=["pay_period_manifest.json","summaries.json","accepted_events.json","exceptions.json","manager_review_report.json","payroll_summary.csv","payroll_summary.html","owner_review.md",f"{pp['period_id']}.zip"]
            checks["pay_period_close_created"]=all((ppdir/x).exists() for x in required)
            checks["pay_period_archive_valid"]=zipfile.is_zipfile(ppdir/f"{pp['period_id']}.zip")
            checks["pay_period_listed"]=any(x.get("period_id")==pp["period_id"] for x in mod.list_pay_periods())
            backup=mod.create_runtime_backup()
            bpath=Path(backup["backup_file"])
            checks["backup_created"]=bpath.exists() and zipfile.is_zipfile(bpath)
            verify=mod.verify_runtime_backup(bpath)
            checks["backup_verify_pass"]=verify.get("ok") is True and verify.get("checked_file_count",0) > 0
            dry=mod.restore_dry_run(bpath, Path(td)/"restore_candidate")
            checks["restore_dry_run_pass"]=dry.get("status")=="pass" and dry.get("extracted_file_count",0) > 0
            issue=mod.create_pilot_issue("medium", "smoke issue", "non-blocking smoke issue")
            checks["pilot_issue_logged"]=issue.get("issue_id","").startswith("pilot_issue_")
            readiness=mod.pilot_readiness_report()
            checks["pilot_readiness_report"]=readiness.get("status") in {"ready", "ready_with_warnings", "blocked"} and "checks" in readiness
            signoff=mod.create_pilot_signoff("Smoke Owner", "owner", "pilot_ready_with_warnings", "smoke signoff")
            checks["pilot_signoff_recorded"]=signoff.get("signoff_id","").startswith("pilot_signoff_")
            pack=mod.create_pilot_acceptance_pack("smoke pilot pack")
            checks["pilot_acceptance_pack_created"]=pack.get("ok") is True and zipfile.is_zipfile(Path(pack["archive_path"]))
            checks["employee_summary_auth"]=mod.employee_summary_auth("emp_001","1234").get("ok") is True
            checks["employee_summary_bad_pin"]=mod.employee_summary_auth("emp_001","0000").get("ok") is False
            checks["setup_warnings_present"]=bool(mod.setup_warnings())
        except Exception as e:
            errors.append(str(e))
    status="pass" if not errors and all(checks.values()) else "fail"
    report={"checked_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"version":VERSION,"status":status,"checks":checks,"errors":errors,"non_claims":["runtime smoke used temporary app copy only","restore proof is dry-run extraction only","pilot acceptance pack is pre-production operator evidence only","no production deployment was performed","no legal/payroll/cannabis compliance seal is claimed"]}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0 if status=="pass" else 1
if __name__=="__main__": sys.exit(main())

#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "repo_scaffold" / "app"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def load_server(path: Path):
    spec = importlib.util.spec_from_file_location("bbtc_v090_validation", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_report(name: str, checks: dict[str, bool], errors: list[str]) -> None:
    report = {
        "version": VERSION,
        "arc": "arc_employee_management_kiosk_timeclock",
        "status": "pass" if not errors and all(checks.values()) else "fail",
        "checks": checks,
        "errors": errors,
        "non_claims": [
            "Temporary runtime fixture only.",
            "No production deployment.",
            "No payroll or tax compliance.",
            "WebSocket is local-network only and retains authenticated HTTP polling fallback.",
        ],
    }
    (ROOT / "validation" / name).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    checks: dict[str, bool] = {}
    errors: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="bbtc_v090_") as td:
            temp_app = Path(td) / "app"
            shutil.copytree(APP, temp_app)
            shutil.rmtree(temp_app / "data", ignore_errors=True)
            module = load_server(temp_app / "server.py")
            module.init_db()

            employee = module.upsert_employee(
                "emp_900", "Arc Test Employee", "9900", "active", "employee",
                25.0, 5.0, 10.0,
            )
            checks["employee_optional_fields"] = (
                employee["hourly_rate"] == 25.0
                and employee["tax_withholding_amount"] == 5.0
                and employee["tax_withholding_percent"] == 10.0
            )
            first = module.record("emp_900", "9900", "clock_in", "arc_validation")
            duplicate = module.record("emp_900", "9900", "clock_in", "arc_validation")
            checks["duplicate_open_session_rejected"] = (
                first["validation_status"] == "accepted"
                and duplicate["validation_status"] == "rejected"
                and "duplicate_open_session" in duplicate["policy_flags"]
            )
            active = module.active_sessions()
            checks["server_authoritative_active_session"] = (
                len(active) == 1
                and active[0]["employee_id"] == "emp_900"
                and active[0]["elapsed_seconds"] >= 0
                and "server_calculated_at_utc" in active[0]
            )
            last = module.record("emp_900", "9900", "clock_out", "arc_validation")
            checks["completed_session"] = last["validation_status"] == "accepted"
            module.upsert_employee("emp_901", "Owner Action Employee", "9901", "active", "employee")
            module.record("emp_901", "9901", "clock_in", "arc_validation")
            owner_employee_out = module.owner_clock_out_live_person("employee", "emp_901")
            checks["owner_live_employee_clock_out"] = (
                owner_employee_out["ok"] is True
                and owner_employee_out["owner_adjustment"]["event"]["event_type"] == "clock_out"
                and not any(row["employee_id"] == "emp_901" for row in module.active_sessions())
            )
            module.add_manual_hours("emp_900", module.utc_now().date().isoformat(), 1.25, "approved validation adjustment")

            employee_csv = module.export("csv")
            with employee_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                employee_rows = list(csv.DictReader(handle))
                employee_headers = list(employee_rows[0]) if employee_rows else []
            expected_employee_headers = [
                "Employee Name", "Employee ID", "Date", "Clock In", "Clock Out",
                "Break Minutes", "Total Hours", "Hourly Rate", "Gross Pay Estimate",
                "Tax Withheld Estimate", "Net Pay Estimate", "Notes",
            ]
            checks["human_employee_csv"] = employee_headers == expected_employee_headers and bool(employee_rows)

            guest = module.guest_sign_in("Guest Example", "Example Org", "Delivery", "validation")
            live_with_guest = module.live_roster_snapshot()
            checks["guest_in_live_roster"] = (
                live_with_guest["active_guest_count"] == 1
                and live_with_guest["active_session_count"] == 1
                and live_with_guest["active_roster"][0]["person_type"] == "guest"
                and live_with_guest["active_roster"][0]["display_name"] == "Guest Example"
            )
            owner_guest_out = module.owner_clock_out_live_person("guest", guest["guest_session_id"])
            checks["owner_live_guest_sign_out"] = (
                owner_guest_out["ok"] is True
                and owner_guest_out["guest_session"]["sign_out_time_utc"] is not None
                and not module.active_guest_sessions()
            )
            guest_csv = module.export_guest_csv()
            with guest_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                guest_rows = list(csv.DictReader(handle))
                guest_headers = list(guest_rows[0]) if guest_rows else []
            checks["separate_guest_csv"] = (
                guest_headers == ["Guest Name", "Organization", "Purpose", "Sign In", "Sign Out", "Visit Duration", "Notes"]
                and bool(guest_rows)
                and guest_csv.parent != employee_csv.parent
            )

            removed = module.set_employee_status("emp_900", "removed")
            checks["soft_delete_preserves_history"] = (
                removed["status"] == "removed"
                and removed["removed_at_utc"] is not None
                and module.valid_emp("emp_900", "9900")[0] is False
                and any(row["employee_id"] == "emp_900" for row in module.calc(module.read_events()))
            )
            restored = module.set_employee_status("emp_900", "active")
            checks["employee_restore"] = restored["status"] == "active" and restored["removed_at_utc"] is None

            summary = module.manager_summary(None, None)
            checks["summary_contract"] = (
                summary["ok"] is True
                and "active_sessions" in summary
                and "active_guest_sessions" in summary
                and "active_roster" in summary
                and "completed_session_count" in summary
                and "total_hours" in summary
                and summary["live_transport"]["mode"] == "websocket_with_http_polling_fallback"
            )
            try:
                module.factory_reset_runtime("WRONG")
                checks["factory_reset_rejects_wrong_phrase"] = False
            except ValueError:
                checks["factory_reset_rejects_wrong_phrase"] = bool(module.read_all_events())
            owner_token_before_reset = module.settings()["owner_token"]
            reset_result = module.factory_reset_runtime("RESET BBTC")
            checks["factory_reset_backup_and_clear"] = (
                reset_result["ok"] is True
                and reset_result["backup_verified"] is True
                and Path(reset_result["backup_file"]).exists()
                and module.settings()["owner_token"] == owner_token_before_reset
                and module.read_all_events() == []
                and module.list_guest_sessions(True) == []
                and module.active_sessions() == []
            )

        html = (APP / "static" / "index.html").read_text(encoding="utf-8")
        visible_owner_html = re.sub(r"<template\b[^>]*>.*?</template>", "", html, flags=re.DOTALL)
        js = (APP / "static" / "app.js").read_text(encoding="utf-8")
        employee_html = (APP / "static" / "employee.html").read_text(encoding="utf-8")
        employee_js = (APP / "static" / "employee.js").read_text(encoding="utf-8")
        checks["summary_button_fixed"] = (
            'id="summary_btn"' in html
            and 'id="timeclock_summary_panel"' in html
            and 'renderSummaryPanel(data)' in js
            and 'employee_management_panel").scrollIntoView' not in js[js.find('$("summary_btn")'):js.find('$("export_btn")')]
        )
        checks["manage_employees_button_fixed"] = (
            ">Manage Employees<" in html
            and 'id="employee_management_panel"' in html
            and "loadEmployeeManagement" in js
        )
        checks["kiosk_manager_lockout"] = (
            'id="guest_sign_in_btn"' in employee_html
            and 'id="guest_sign_out_btn"' in employee_html
            and 'id="active_guest_list"' not in employee_html
            and "owner_token" not in employee_html
            and "employee_management_panel" not in employee_html
            and "sessionStorage" not in employee_js
        )
        checks["shared_kiosk_next_person_reset"] = (
            "clearPrivateFields" in employee_js
            and "scheduleReadyReset" in employee_js
            and "/kiosk/live" in employee_js
            and "active_guest_sessions" not in employee_js
        )
        checks["websocket_with_polling_fallback"] = (
            "start_live_websocket_server" in (APP / "server.py").read_text(encoding="utf-8")
            and "connectOwnerLive" in js
            and "Polling fallback" in html
            and "Live WebSocket" in js
        )
        checks["owner_actionable_onsite_roster"] = (
            'data-roster-filter="employee"' in html
            and 'data-roster-filter="guest"' in html
            and "View Information" in js
            and "Clock Out Employee" in js
            and "Sign Guest Out" in js
            and "/api/owner/live/clock-out" in (APP / "server.py").read_text(encoding="utf-8")
        )
        checks["screen_and_factory_reset_controls"] = (
            'id="reset_screen_btn"' in html
            and 'id="factory_reset_btn"' in html
            and 'id="factory_reset_phrase"' in html
            and "resetOwnerScreen" in js
            and "/api/owner/factory-reset" in (APP / "server.py").read_text(encoding="utf-8")
        )
        poster_html = (APP / "static" / "kiosk_poster.html").read_text(encoding="utf-8")
        poster_js = (APP / "static" / "kiosk_poster.js").read_text(encoding="utf-8")
        checks["printable_kiosk_qr_poster"] = (
            'id="print_kiosk_poster_btn"' in html
            and 'id="poster_notice_enabled"' in html
            and "/kiosk-poster" in (APP / "server.py").read_text(encoding="utf-8")
            and 'id="poster_qr"' in poster_html
            and 'id="poster_access_notice"' in poster_html
            and "parameters.get(\"notice\")" in poster_js
            and "window.print()" in poster_js
            and "@media print" in (APP / "static" / "style.css").read_text(encoding="utf-8")
        )
        checks["authorized_access_notice"] = (
            "No unauthorized entry beyond this point" in employee_html
            and "employees and registered visitors" in employee_html
            and "kiosk-access-notice" in employee_html
        )
        checks["owner_kiosk_surface_separation"] = (
            'class="station-grid owner-only-grid"' in visible_owner_html
            and '<a class="punch-btn primary kiosk-launch-link" href="/employee">Open Time Clock Kiosk</a>' in visible_owner_html
            and 'id="guest_sign_in_btn"' not in visible_owner_html
            and 'data-punch-action=' not in visible_owner_html
        )

        required = [
            "contracts/employee/employee_record.v1.schema.json",
            "contracts/timeclock/active_session.v1.schema.json",
            "contracts/guest/guest_sign_in.v1.schema.json",
            "contracts/export/human_readable_csv.v1.schema.json",
            "contracts/realtime/live_clocked_in_status.v1.schema.json",
            "pipeline/arc_employee_management_kiosk_timeclock.v0.9.0.json",
            "docs/SYSTEM_STATE_CURRENT.md",
        ]
        checks["required_arc_files"] = all((ROOT / path).exists() for path in required)
    except Exception as error:
        errors.append(f"{type(error).__name__}: {error}")

    failed = [key for key, value in checks.items() if not value]
    errors.extend(f"check_failed:{key}" for key in failed)
    report_map = {
        "employee_management_validation_report.json": ["employee_optional_fields", "soft_delete_preserves_history", "employee_restore"],
        "kiosk_mode_validation_report.json": ["duplicate_open_session_rejected", "kiosk_manager_lockout", "owner_kiosk_surface_separation", "shared_kiosk_next_person_reset", "owner_live_employee_clock_out", "printable_kiosk_qr_poster", "authorized_access_notice"],
        "guest_export_validation_report.json": ["separate_guest_csv", "guest_in_live_roster", "owner_live_guest_sign_out"],
        "csv_format_validation_report.json": ["human_employee_csv", "separate_guest_csv"],
        "realtime_status_validation_report.json": ["server_authoritative_active_session", "summary_contract", "guest_in_live_roster", "websocket_with_polling_fallback", "owner_actionable_onsite_roster"],
        "summary_button_bugfix_validation_report.json": ["summary_button_fixed", "manage_employees_button_fixed", "screen_and_factory_reset_controls", "factory_reset_rejects_wrong_phrase", "factory_reset_backup_and_clear"],
    }
    for filename, names in report_map.items():
        subset = {name: checks.get(name, False) for name in names}
        subset_errors = [error for error in errors if any(name in error for name in names)]
        write_report(filename, subset, subset_errors)
    print(json.dumps({"version": VERSION, "status": "pass" if not errors else "fail", "checks": checks, "errors": errors}, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

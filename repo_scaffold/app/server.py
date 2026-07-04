#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import hmac
import html
import ipaddress
import json
import mimetypes
import os
import re
import secrets
import shutil
import socket
import sqlite3
import tempfile
import threading
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    from websockets.exceptions import ConnectionClosed
    from websockets.sync.server import serve as websocket_serve
except ImportError:
    ConnectionClosed = Exception
    websocket_serve = None

APP_VERSION = "0.9.0"
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
CONFIG_DIR = APP_DIR / "config"
STATIC_DIR = APP_DIR / "static"
LEDGER_DIR = DATA_DIR / "ledger" / "clock_events"
EXPORT_DIR = DATA_DIR / "exports"
BACKUP_DIR = DATA_DIR / "backups"
RESTORE_DIR = DATA_DIR / "restore_candidates"
PAY_PERIOD_DIR = DATA_DIR / "pay_periods"
PILOT_DIR = DATA_DIR / "pilot"
CSV_LEDGER_DIR = DATA_DIR / "csv_ledger" / "clock_events"
OFFLINE_SYNC_DIR = DATA_DIR / "offline_sync"
GUEST_LEDGER_DIR = DATA_DIR / "ledger" / "guest_sessions"
GUEST_EXPORT_DIR = DATA_DIR / "exports" / "guests"
DB_PATH = DATA_DIR / "timeclock.sqlite3"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
EMPLOYEES_PATH = CONFIG_DIR / "employees.seed.json"
EVENT_TYPES = {"clock_in", "clock_out", "break_start", "break_end"}
DEFAULT_OWNER_TOKEN = "CHANGE_ME_OWNER_TOKEN"
DEFAULT_PIN_PEPPER = "CHANGE_ME_PIN_PEPPER"
OWNER_TOKEN_UPDATE_LOCK = threading.Lock()
FACTORY_RESET_LOCK = threading.Lock()
OWNER_BACKUP_TOKEN_COUNT = 10
LIVE_CONNECTIONS: set = set()
KIOSK_CONNECTIONS: set = set()
LIVE_CONNECTIONS_LOCK = threading.Lock()
LIVE_WEBSOCKET_STATE = {
    "available": False,
    "host": None,
    "port": None,
    "error": "not_started",
}


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def sha_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def settings() -> dict:
    base = {
        "app_security_policy_version": "0.7.1",
        "site_id": "best_buds_west_warwick_ri",
        "site_display_name": "Best Buds Cannabis Cultivation — West Warwick, RI",
        "terminal_id": "front_kiosk_01",
        "owner_token": DEFAULT_OWNER_TOKEN,
        "timezone": "America/New_York",
        "pin_pepper": DEFAULT_PIN_PEPPER,
        "regular_hours_cap_per_week": 40,
        "min_pin_length": 4,
        "allow_owner_adjustments": True,
        "owner_adjustment_reason_required": True,
        "manager_review_required_before_pay_period_close": False,
        "allowed_export_formats": ["csv", "json", "markdown", "html"],
        "setup_required_when_default_secret": True,
        "clock_events": sorted(EVENT_TYPES),
        "pilot_policy": {
            "pilot_mode_enabled": True,
            "readiness_check_required_before_live_pilot": True,
            "issue_log_required": True,
            "owner_signoff_required": True,
            "employee_training_acknowledgement_recommended": True,
            "max_pilot_days_before_review": 14
        },
    }
    base.update(load_json(SETTINGS_PATH, {}))
    return base


def setup_warnings() -> list[str]:
    s = settings()
    out = []
    if s.get("owner_token") == DEFAULT_OWNER_TOKEN:
        out.append("owner_token_default_change_required")
    if s.get("pin_pepper") == DEFAULT_PIN_PEPPER:
        out.append("pin_pepper_default_change_required")
    if int(s.get("min_pin_length", 4)) < 4:
        out.append("min_pin_length_below_recommended_floor")
    return out


def ensure_dirs() -> None:
    for p in [DATA_DIR, CONFIG_DIR, LEDGER_DIR, EXPORT_DIR, BACKUP_DIR, RESTORE_DIR, PAY_PERIOD_DIR, PILOT_DIR, CSV_LEDGER_DIR, OFFLINE_SYNC_DIR, GUEST_LEDGER_DIR, GUEST_EXPORT_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def pin_hash(employee_id: str, pin: str) -> str:
    return sha_text(f"{employee_id}:{pin}:{settings()['pin_pepper']}")


def init_db() -> None:
    ensure_dirs()
    con = sqlite3.connect(DB_PATH)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS employees(
            employee_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            pin_hash TEXT NOT NULL,
            status TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS guest_sessions(
            guest_session_id TEXT PRIMARY KEY,
            guest_name TEXT NOT NULL,
            organization TEXT,
            purpose TEXT,
            sign_in_time_utc TEXT NOT NULL,
            sign_out_time_utc TEXT,
            notes TEXT,
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS manual_hours_adjustments(
            adjustment_id TEXT PRIMARY KEY,
            employee_id TEXT NOT NULL,
            work_date TEXT NOT NULL,
            hours REAL NOT NULL,
            reason TEXT NOT NULL,
            created_at_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS clock_events(
            event_id TEXT PRIMARY KEY,
            employee_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            captured_at_utc TEXT NOT NULL,
            captured_local TEXT NOT NULL,
            source TEXT NOT NULL,
            validation_status TEXT NOT NULL,
            event_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_receipts(
            receipt_id TEXT PRIMARY KEY,
            receipt_type TEXT NOT NULL,
            captured_at_utc TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pay_period_closures(
            period_id TEXT PRIMARY KEY,
            start TEXT,
            end TEXT,
            closed_at_utc TEXT NOT NULL,
            manifest_path TEXT NOT NULL,
            archive_path TEXT NOT NULL,
            manifest_hash TEXT NOT NULL,
            source_ledger_hash TEXT NOT NULL,
            status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS owner_adjustments(
            adjustment_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            employee_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            adjusted_event_time_utc TEXT NOT NULL,
            reason TEXT NOT NULL,
            owner_note TEXT,
            created_at_utc TEXT NOT NULL,
            event_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pilot_issues(
            issue_id TEXT PRIMARY KEY,
            severity TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            details TEXT,
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL,
            payload_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pilot_signoffs(
            signoff_id TEXT PRIMARY KEY,
            signoff_role TEXT NOT NULL,
            signer_name TEXT NOT NULL,
            decision TEXT NOT NULL,
            notes TEXT,
            created_at_utc TEXT NOT NULL,
            readiness_status TEXT NOT NULL,
            payload_hash TEXT NOT NULL
        );
        """
    )
    employee_columns = {row[1] for row in con.execute("PRAGMA table_info(employees)").fetchall()}
    for name, ddl in {
        "hourly_rate": "REAL",
        "tax_withholding_amount": "REAL",
        "tax_withholding_percent": "REAL",
        "removed_at_utc": "TEXT",
    }.items():
        if name not in employee_columns:
            con.execute(f"ALTER TABLE employees ADD COLUMN {name} {ddl}")
    if not EMPLOYEES_PATH.exists():
        EMPLOYEES_PATH.write_text(
            json.dumps(
                [
                    {
                        "employee_id": "emp_001",
                        "display_name": "Sample Employee",
                        "pin": "1234",
                        "status": "active",
                        "role": "employee",
                    }
                ],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    now = utc_now().isoformat()
    for e in json.loads(EMPLOYEES_PATH.read_text(encoding="utf-8")):
        con.execute(
            """
            INSERT OR IGNORE INTO employees(
                employee_id,display_name,pin_hash,status,role,created_at_utc,updated_at_utc,
                hourly_rate,tax_withholding_amount,tax_withholding_percent,removed_at_utc
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                str(e["employee_id"]),
                str(e["display_name"]),
                e.get("pin_hash") or pin_hash(str(e["employee_id"]), str(e.get("pin", ""))),
                str(e.get("status", "active")),
                str(e.get("role", "employee")),
                str(e.get("created_at_utc", now)),
                str(e.get("updated_at_utc", now)),
                e.get("hourly_rate"),
                e.get("tax_withholding_amount"),
                e.get("tax_withholding_percent"),
                e.get("removed_at_utc"),
            ),
        )
    con.commit()
    con.close()


def db_rows(sql: str, args=()) -> list[dict]:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(sql, args).fetchall()]
    con.close()
    return rows


def db_execute(sql: str, args=()) -> None:
    con = sqlite3.connect(DB_PATH)
    con.execute(sql, args)
    con.commit()
    con.close()


def employee_lookup() -> dict[str, dict]:
    return {
        r["employee_id"]: r
        for r in db_rows(
            """
            SELECT employee_id,display_name,status,role,hourly_rate,
                   tax_withholding_amount,tax_withholding_percent,removed_at_utc
            FROM employees ORDER BY employee_id
            """
        )
    }


def list_employees(include_inactive: bool = True) -> list[dict]:
    columns = """
        employee_id,display_name,status,role,created_at_utc,updated_at_utc,
        hourly_rate,tax_withholding_amount,tax_withholding_percent,removed_at_utc
    """
    if include_inactive:
        return db_rows(f"SELECT {columns} FROM employees ORDER BY status,display_name,employee_id")
    return db_rows(f"SELECT {columns} FROM employees WHERE status='active' ORDER BY display_name,employee_id")


def optional_float(value, field: str) -> float | None:
    if value in (None, ""):
        return None
    number = float(value)
    if number < 0:
        raise ValueError(f"{field}_must_be_nonnegative")
    return round(number, 2)


def upsert_employee(
    employee_id: str,
    display_name: str,
    pin: str,
    status: str = "active",
    role: str = "employee",
    hourly_rate=None,
    tax_withholding_amount=None,
    tax_withholding_percent=None,
) -> dict:
    if not employee_id or not display_name:
        raise ValueError("employee_id_display_name_required")
    existing = db_rows(
        """
        SELECT pin_hash,created_at_utc,hourly_rate,tax_withholding_amount,tax_withholding_percent
        FROM employees WHERE employee_id=?
        """,
        (employee_id,),
    )
    if not pin and not existing:
        raise ValueError("pin_required_for_new_employee")
    if pin and len(str(pin)) < int(settings().get("min_pin_length", 4)):
        raise ValueError("pin_below_min_length")
    if status not in {"active", "inactive", "removed"}:
        raise ValueError("unsupported_employee_status")
    if role not in {"employee", "manager", "owner"}:
        raise ValueError("unsupported_employee_role")
    now = utc_now().isoformat()
    ph = pin_hash(employee_id, pin) if pin else existing[0]["pin_hash"]
    created_at = existing[0]["created_at_utc"] if existing else now
    rate = optional_float(
        existing[0]["hourly_rate"] if existing and hourly_rate in (None, "") else hourly_rate,
        "hourly_rate",
    )
    tax_amount = optional_float(
        existing[0]["tax_withholding_amount"] if existing and tax_withholding_amount in (None, "") else tax_withholding_amount,
        "tax_withholding_amount",
    )
    tax_percent = optional_float(
        existing[0]["tax_withholding_percent"] if existing and tax_withholding_percent in (None, "") else tax_withholding_percent,
        "tax_withholding_percent",
    )
    if tax_percent is not None and tax_percent > 100:
        raise ValueError("tax_withholding_percent_above_100")
    removed_at = now if status == "removed" else None
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """
        INSERT INTO employees(
            employee_id,display_name,pin_hash,status,role,created_at_utc,updated_at_utc,
            hourly_rate,tax_withholding_amount,tax_withholding_percent,removed_at_utc
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(employee_id) DO UPDATE SET
            display_name=excluded.display_name,
            pin_hash=excluded.pin_hash,
            status=excluded.status,
            role=excluded.role,
            updated_at_utc=excluded.updated_at_utc,
            hourly_rate=excluded.hourly_rate,
            tax_withholding_amount=excluded.tax_withholding_amount,
            tax_withholding_percent=excluded.tax_withholding_percent,
            removed_at_utc=excluded.removed_at_utc
        """,
        (employee_id, display_name, ph, status, role, created_at, now, rate, tax_amount, tax_percent, removed_at),
    )
    con.commit()
    con.close()
    receipt = {
        "receipt_id": f"employee_upsert_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "receipt_type": "employee_upsert",
        "employee_id": employee_id,
        "status": status,
        "role": role,
        "captured_at_utc": now,
    }
    write_audit_receipt(receipt)
    return {
        "employee_id": employee_id,
        "display_name": display_name,
        "status": status,
        "role": role,
        "hourly_rate": rate,
        "tax_withholding_amount": tax_amount,
        "tax_withholding_percent": tax_percent,
        "removed_at_utc": removed_at,
        "created_at_utc": created_at,
        "updated_at_utc": now,
    }


def set_employee_status(employee_id: str, status: str) -> dict:
    if status not in {"active", "inactive", "removed"}:
        raise ValueError("unsupported_employee_status")
    rows = db_rows("SELECT employee_id FROM employees WHERE employee_id=?", (employee_id,))
    if not rows:
        raise ValueError("employee_not_found")
    now = utc_now().isoformat()
    removed_at = now if status == "removed" else None
    db_execute(
        "UPDATE employees SET status=?,removed_at_utc=?,updated_at_utc=? WHERE employee_id=?",
        (status, removed_at, now, employee_id),
    )
    write_audit_receipt(
        {
            "receipt_type": "employee_status_changed",
            "employee_id": employee_id,
            "status": status,
        }
    )
    return next(e for e in list_employees(True) if e["employee_id"] == employee_id)


def permanently_delete_employee(employee_id: str, confirmation: str) -> dict:
    employee_id = str(employee_id).strip()
    rows = db_rows(
        "SELECT employee_id,display_name,status FROM employees WHERE employee_id=?",
        (employee_id,),
    )
    if not rows:
        raise ValueError("employee_not_found")
    employee = rows[0]
    if employee["status"] != "removed":
        raise ValueError("employee_must_be_removed_first")
    if confirmation != f"DELETE {employee_id}":
        raise ValueError("employee_delete_confirmation_invalid")
    if any(session["employee_id"] == employee_id for session in active_sessions()):
        raise ValueError("employee_has_active_session")
    if db_rows(
        "SELECT adjustment_id FROM manual_hours_adjustments WHERE employee_id=? LIMIT 1",
        (employee_id,),
    ):
        raise ValueError("employee_has_manual_adjustments")
    if any(event.get("employee_id") == employee_id for event in read_all_events()):
        raise ValueError("employee_has_time_history")

    deleted_at = utc_now().isoformat()
    db_execute("DELETE FROM employees WHERE employee_id=?", (employee_id,))
    receipt = write_audit_receipt(
        {
            "receipt_type": "employee_permanently_deleted",
            "employee_id": employee_id,
            "display_name": employee["display_name"],
            "prior_status": employee["status"],
            "deleted_at_utc": deleted_at,
            "deletion_reason": "history_free_employee_record_cleanup",
        }
    )
    return {
        "ok": True,
        "deleted": True,
        "employee_id": employee_id,
        "display_name": employee["display_name"],
        "deleted_at_utc": deleted_at,
        "audit_receipt_id": receipt["receipt_id"],
    }


def add_manual_hours(employee_id: str, work_date: str, hours, reason: str) -> dict:
    if employee_id not in employee_lookup():
        raise ValueError("employee_not_found")
    parsed_date = dt.date.fromisoformat(str(work_date))
    amount = float(hours)
    if amount == 0 or abs(amount) > 24:
        raise ValueError("manual_hours_adjustment_out_of_range")
    if not str(reason).strip():
        raise ValueError("manual_hours_reason_required")
    adjustment = {
        "adjustment_id": f"hours_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "employee_id": employee_id,
        "work_date": parsed_date.isoformat(),
        "hours": round(amount, 2),
        "reason": str(reason).strip(),
        "created_at_utc": utc_now().isoformat(),
    }
    db_execute(
        "INSERT INTO manual_hours_adjustments VALUES(?,?,?,?,?,?)",
        tuple(adjustment.values()),
    )
    write_audit_receipt({"receipt_type": "manual_hours_adjustment", **adjustment})
    return adjustment


def write_audit_receipt(payload: dict) -> dict:
    p = dict(payload)
    p.setdefault("receipt_id", f"receipt_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}")
    p.setdefault("captured_at_utc", utc_now().isoformat())
    p.setdefault("receipt_type", "runtime_audit")
    payload_json = json.dumps(p, sort_keys=True, separators=(",", ":"))
    payload_hash = sha_text(payload_json)
    db_execute(
        "INSERT OR REPLACE INTO audit_receipts VALUES(?,?,?,?,?)",
        (p["receipt_id"], p["receipt_type"], p["captured_at_utc"], payload_json, payload_hash),
    )
    p["payload_hash"] = payload_hash
    return p


def ledger_path() -> Path:
    n = utc_now()
    p = LEDGER_DIR / f"{n.year:04d}" / f"{n.month:02d}" / f"clock_events_{n.year:04d}-{n.month:02d}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def csv_ledger_path_for_event(event: dict | None = None) -> Path:
    ts = None
    if event and event.get("captured_at_utc"):
        try:
            ts = parse_dt(str(event.get("captured_at_utc")))
        except Exception:
            ts = None
    n = ts or utc_now()
    p = CSV_LEDGER_DIR / f"{n.year:04d}" / f"{n.month:02d}" / f"clock_events_{n.year:04d}-{n.month:02d}.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def append_csv_ledger_mirror(event: dict) -> dict:
    """Append an owner-readable CSV mirror row after JSONL ledger write.

    JSONL remains the canonical audit ledger. CSV is a convenience/recovery mirror.
    CSV write warnings are returned but must not invalidate the canonical JSONL write.
    """
    fields = [
        "event_id", "employee_id", "site_id", "terminal_id", "event_type",
        "captured_at_utc", "captured_local", "source", "auth_method",
        "validation_status", "policy_flags", "admin_adjustment", "event_hash"
    ]
    p = csv_ledger_path_for_event(event)
    new_file = not p.exists()
    try:
        with p.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            if new_file:
                w.writeheader()
            row = {k: event.get(k, "") for k in fields}
            if isinstance(row.get("policy_flags"), list):
                row["policy_flags"] = "|".join(str(x) for x in row["policy_flags"])
            w.writerow(row)
        return {"ok": True, "csv_ledger_file": str(p), "warning": None}
    except Exception as exc:
        return {"ok": False, "csv_ledger_file": str(p), "warning": f"csv_ledger_mirror_write_failed:{exc}"}



def iter_ledger_lines():
    for p in sorted(LEDGER_DIR.glob("**/*.jsonl")):
        for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                yield p, lineno, line


def last_hash() -> str:
    last = "sha256:GENESIS"
    for _p, _lineno, line in iter_ledger_lines():
        last = json.loads(line).get("event_hash", "sha256:UNKNOWN")
    return last


def event_hash(event: dict) -> str:
    e = dict(event)
    e.pop("event_hash", None)
    return sha_text(json.dumps(e, sort_keys=True, separators=(",", ":")))


def valid_emp(employee_id: str, pin: str) -> tuple[bool, str]:
    rows = db_rows("SELECT pin_hash,status FROM employees WHERE employee_id=?", (employee_id,))
    if not rows:
        return False, "employee_not_found"
    expected, status = rows[0]["pin_hash"], rows[0]["status"]
    if status != "active":
        return False, "employee_inactive"
    if not hmac.compare_digest(expected, pin_hash(employee_id, pin)):
        return False, "pin_invalid"
    return True, "ok"


def local_iso_for(ts: dt.datetime | None = None) -> str:
    base = ts or utc_now()
    if base.tzinfo is None:
        base = base.replace(tzinfo=dt.timezone.utc)
    base = base.astimezone(dt.timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return base.astimezone(ZoneInfo(settings()["timezone"])).isoformat()
    except Exception:
        return base.astimezone().isoformat()


def local_iso() -> str:
    return local_iso_for(utc_now())


def record(employee_id: str, pin: str, event_type: str, source: str = "web_index") -> dict:
    if event_type not in EVENT_TYPES:
        raise ValueError("unsupported_event_type")
    ok, reason = valid_emp(employee_id, pin)
    if ok:
        current_status = employee_clock_state(employee_id).get("current_status")
        transition_errors = {
            ("clocked_in", "clock_in"): "duplicate_open_session",
            ("on_break", "clock_in"): "duplicate_open_session",
            ("clocked_out", "clock_out"): "clock_out_without_open_session",
            ("clocked_out", "break_start"): "break_start_without_open_session",
            ("on_break", "break_start"): "duplicate_break_start",
            ("clocked_out", "break_end"): "break_end_without_open_break",
            ("clocked_in", "break_end"): "break_end_without_open_break",
        }
        transition_error = transition_errors.get((str(current_status), event_type))
        if transition_error:
            ok, reason = False, transition_error
    s = settings()
    now_utc = utc_now().isoformat()
    ev = {
        "event_id": f"clk_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "employee_id": employee_id,
        "site_id": s["site_id"],
        "terminal_id": s["terminal_id"],
        "event_type": event_type,
        "captured_at_utc": now_utc,
        "captured_local": local_iso(),
        "local_timezone": s["timezone"],
        "source": source,
        "auth_method": "pin",
        "validation_status": "accepted" if ok else "rejected",
        "policy_flags": [] if ok else [reason],
        "notes": "",
        "admin_adjustment": False,
        "prev_event_hash": last_hash(),
        "event_hash": "",
    }
    ev["event_hash"] = event_hash(ev)
    with ledger_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(ev, sort_keys=True) + "\n")
    csv_receipt = append_csv_ledger_mirror(ev)
    if not csv_receipt.get("ok"):
        ev.setdefault("mirror_warnings", []).append(csv_receipt.get("warning"))
    if ok:
        db_execute(
            "INSERT INTO clock_events VALUES(?,?,?,?,?,?,?,?)",
            (
                ev["event_id"],
                ev["employee_id"],
                ev["event_type"],
                ev["captured_at_utc"],
                ev["captured_local"],
                ev["source"],
                ev["validation_status"],
                ev["event_hash"],
            ),
        )
    return ev


def parse_dt(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    if len(value) == 10:
        value = value + "T00:00:00+00:00"
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def reporting_timezone():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(settings()["timezone"])
    except Exception:
        return dt.datetime.now().astimezone().tzinfo or dt.timezone.utc


def reporting_date_bound(value: str, end_exclusive: bool = False) -> dt.datetime:
    local_date = dt.date.fromisoformat(str(value)[:10])
    if end_exclusive:
        local_date += dt.timedelta(days=1)
    local_value = dt.datetime.combine(local_date, dt.time.min, tzinfo=reporting_timezone())
    return local_value.astimezone(dt.timezone.utc)


def reporting_range_contract(start: str | None, end: str | None) -> dict:
    if bool(start) != bool(end):
        raise ValueError("reporting_period_requires_start_and_end")
    if not start and not end:
        return {
            "mode": "all_time",
            "start_date": None,
            "end_date": None,
            "inclusive": True,
            "timezone": settings()["timezone"],
            "start_utc": None,
            "end_exclusive_utc": None,
            "label": "All available records",
        }
    start_date = dt.date.fromisoformat(str(start)[:10])
    end_date = dt.date.fromisoformat(str(end)[:10])
    if start_date > end_date:
        raise ValueError("reporting_period_start_after_end")
    start_utc = reporting_date_bound(start_date.isoformat())
    end_exclusive_utc = reporting_date_bound(end_date.isoformat(), True)
    return {
        "mode": "selected_period",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "inclusive": True,
        "timezone": settings()["timezone"],
        "start_utc": start_utc.isoformat(),
        "end_exclusive_utc": end_exclusive_utc.isoformat(),
        "label": f"{start_date.isoformat()} through {end_date.isoformat()}",
    }


def read_events(start: str | None = None, end: str | None = None) -> list[dict]:
    start_dt = reporting_date_bound(start) if start and len(str(start)) == 10 else parse_dt(start)
    end_dt = (
        reporting_date_bound(end, True) - dt.timedelta(microseconds=1)
        if end and len(str(end)) == 10
        else parse_dt(end)
    )
    if start_dt and end_dt and start_dt > end_dt:
        raise ValueError("reporting_period_start_after_end")
    out = []
    for _p, _lineno, line in iter_ledger_lines():
        e = json.loads(line)
        if e.get("validation_status") != "accepted":
            continue
        ts = parse_dt(e["captured_at_utc"])
        if start_dt and ts < start_dt:
            continue
        if end_dt and ts > end_dt:
            continue
        out.append(e)
    return sorted(out, key=lambda e: (e["employee_id"], e["captured_at_utc"], e["event_id"]))


def week_key(ts: dt.datetime) -> str:
    iso = ts.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def calc(events: list[dict]) -> list[dict]:
    by: dict[str, list[dict]] = {}
    names = employee_lookup()
    for e in events:
        by.setdefault(e["employee_id"], []).append(e)
    rows = []
    cap = float(settings().get("regular_hours_cap_per_week", 40))
    for emp, evs in sorted(by.items()):
        open_clock = None
        open_break = None
        work_by_week: dict[str, float] = {}
        break_seconds = 0.0
        exc: list[str] = []
        for e in sorted(evs, key=lambda x: (x["captured_at_utc"], x["event_id"])):
            t = parse_dt(e["captured_at_utc"])
            assert t is not None
            if e["event_type"] == "clock_in":
                if open_clock:
                    exc.append("duplicate_clock_in:" + e["event_id"])
                else:
                    open_clock = t
            elif e["event_type"] == "clock_out":
                if not open_clock:
                    exc.append("clock_out_without_clock_in:" + e["event_id"])
                else:
                    if open_break:
                        break_seconds += (t - open_break).total_seconds()
                        open_break = None
                        exc.append("break_auto_closed_by_clock_out:" + e["event_id"])
                    seconds = max((t - open_clock).total_seconds(), 0)
                    work_by_week[week_key(open_clock)] = work_by_week.get(week_key(open_clock), 0.0) + seconds
                    open_clock = None
            elif e["event_type"] == "break_start":
                if not open_clock:
                    exc.append("break_start_while_not_clocked_in:" + e["event_id"])
                elif open_break:
                    exc.append("duplicate_break_start:" + e["event_id"])
                else:
                    open_break = t
            elif e["event_type"] == "break_end":
                if not open_break:
                    exc.append("break_end_without_break_start:" + e["event_id"])
                else:
                    break_seconds += max((t - open_break).total_seconds(), 0)
                    open_break = None
        if open_clock:
            exc.append("open_clock_session")
        if open_break:
            exc.append("open_break_session")
        gross_seconds = sum(work_by_week.values())
        break_hours = round(break_seconds / 3600, 2)
        net_hours = max(gross_seconds / 3600 - break_hours, 0)
        regular = 0.0
        overtime = 0.0
        week_breakdown = []
        for wk, sec in sorted(work_by_week.items()):
            hrs = max(sec / 3600, 0)
            r = min(hrs, cap)
            o = max(hrs - cap, 0)
            regular += r
            overtime += o
            week_breakdown.append({"week": wk, "gross_hours": round(hrs, 2), "regular_hours": round(r, 2), "overtime_hours": round(o, 2)})
        rows.append(
            {
                "employee_id": emp,
                "display_name": names.get(emp, {}).get("display_name", emp),
                "gross_work_hours": round(max(gross_seconds / 3600, 0), 2),
                "break_hours": break_hours,
                "net_work_hours": round(net_hours, 2),
                "regular_hours_estimate": round(regular, 2),
                "overtime_hours_estimate": round(overtime, 2),
                "exceptions": exc,
                "source_event_count": len(evs),
                "week_breakdown": week_breakdown,
            }
        )

    return rows


def local_day_bounds(day: str | None = None) -> tuple[dt.datetime, dt.datetime, str]:
    """Return UTC start/end bounds for a local business day."""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(settings()["timezone"])
    except Exception:
        tz = dt.datetime.now().astimezone().tzinfo or dt.timezone.utc
    if day:
        local_date = dt.date.fromisoformat(str(day)[:10])
    else:
        local_date = utc_now().astimezone(tz).date()
    start_local = dt.datetime.combine(local_date, dt.time.min, tzinfo=tz)
    end_local = start_local + dt.timedelta(days=1)
    return start_local.astimezone(dt.timezone.utc), end_local.astimezone(dt.timezone.utc), local_date.isoformat()


def employee_clock_state(employee_id: str, events: list[dict] | None = None) -> dict:
    evs = [e for e in (events if events is not None else read_events()) if e.get("employee_id") == employee_id and e.get("validation_status") == "accepted"]
    open_clock = None
    open_break = None
    for e in sorted(evs, key=lambda x: (x.get("captured_at_utc", ""), x.get("event_id", ""))):
        t = parse_dt(e.get("captured_at_utc"))
        if e.get("event_type") == "clock_in":
            open_clock = t
            open_break = None
        elif e.get("event_type") == "clock_out":
            open_clock = None
            open_break = None
        elif e.get("event_type") == "break_start" and open_clock:
            open_break = t
        elif e.get("event_type") == "break_end":
            open_break = None
    if open_break:
        status = "on_break"
    elif open_clock:
        status = "clocked_in"
    else:
        status = "clocked_out"
    return {
        "employee_id": employee_id,
        "current_status": status,
        "open_clock_started_at_utc": open_clock.isoformat() if open_clock else None,
        "open_break_started_at_utc": open_break.isoformat() if open_break else None,
    }


def employee_day_summary(employee_id: str, day: str | None = None) -> dict:
    start_utc, end_utc, local_day = local_day_bounds(day)
    evs = [e for e in read_events(start_utc.isoformat(), end_utc.isoformat()) if e.get("employee_id") == employee_id]
    rows = calc(evs)
    row = rows[0] if rows else {
        "employee_id": employee_id,
        "display_name": employee_lookup().get(employee_id, {}).get("display_name", employee_id),
        "gross_work_hours": 0.0,
        "break_hours": 0.0,
        "net_work_hours": 0.0,
        "regular_hours_estimate": 0.0,
        "overtime_hours_estimate": 0.0,
        "exceptions": [],
        "source_event_count": 0,
        "week_breakdown": [],
    }
    state = employee_clock_state(employee_id, evs)
    return {
        "employee_id": employee_id,
        "display_name": row.get("display_name", employee_id),
        "local_day": local_day,
        "local_timezone": settings()["timezone"],
        "gross_work_hours": row.get("gross_work_hours", 0.0),
        "break_hours": row.get("break_hours", 0.0),
        "net_work_hours": row.get("net_work_hours", 0.0),
        "regular_hours_estimate": row.get("regular_hours_estimate", 0.0),
        "overtime_hours_estimate": row.get("overtime_hours_estimate", 0.0),
        "exceptions": row.get("exceptions", []),
        "source_event_count": row.get("source_event_count", 0),
        "current_status": state.get("current_status"),
        "open_clock_started_at_utc": state.get("open_clock_started_at_utc"),
        "open_break_started_at_utc": state.get("open_break_started_at_utc"),
    }


def employee_last_punch(employee_id: str, day: str | None = None) -> dict | None:
    start_utc, end_utc, _local_day = local_day_bounds(day)
    evs = [
        e for e in read_events(start_utc.isoformat(), end_utc.isoformat())
        if e.get("employee_id") == employee_id and e.get("validation_status") == "accepted"
    ]
    if not evs:
        return None
    last = max(evs, key=lambda e: e.get("captured_at_utc", ""))
    return {
        "event_id": last.get("event_id"),
        "event_type": last.get("event_type"),
        "captured_at_utc": last.get("captured_at_utc"),
        "captured_local": last.get("captured_local"),
    }


def employee_summary_auth(employee_id: str, pin: str) -> dict:
    ok, reason = valid_emp(employee_id, pin)
    if not ok:
        return {"ok": False, "error": reason}
    return {
        "ok": True,
        "today_summary": employee_day_summary(employee_id),
        "last_punch": employee_last_punch(employee_id),
        "non_claims": [
            "Today hours are calculated from accepted ledger events in this runtime.",
            "This summary is not payroll approval.",
        ],
    }


def active_sessions() -> list[dict]:
    now = utc_now()
    events = read_events()
    employees = employee_lookup()
    sessions = []
    for employee_id, employee in employees.items():
        state = employee_clock_state(employee_id, events)
        started = parse_dt(state.get("open_clock_started_at_utc"))
        if not started:
            continue
        sessions.append(
            {
                "employee_id": employee_id,
                "display_name": employee.get("display_name", employee_id),
                "employee_status": employee.get("status"),
                "employee_role": employee.get("role", "employee"),
                "current_status": state.get("current_status"),
                "clocked_in_at_utc": started.isoformat(),
                "clocked_in_at_local": local_iso_for(started),
                "elapsed_seconds": max(int((now - started).total_seconds()), 0),
                "elapsed_hours": round(max((now - started).total_seconds(), 0) / 3600, 2),
                "open_break_started_at_utc": state.get("open_break_started_at_utc"),
                "requires_manager_review": employee.get("status") != "active",
                "server_calculated_at_utc": now.isoformat(),
            }
        )
    return sorted(sessions, key=lambda item: item["clocked_in_at_utc"])


def active_guest_sessions() -> list[dict]:
    now = utc_now()
    sessions = []
    for guest in list_guest_sessions(False):
        started = parse_dt(guest.get("sign_in_time_utc"))
        if not started:
            continue
        sessions.append(
            {
                "guest_session_id": guest["guest_session_id"],
                "display_name": guest["guest_name"],
                "organization": guest.get("organization") or "",
                "purpose": guest.get("purpose") or "",
                "signed_in_at_utc": started.isoformat(),
                "signed_in_at_local": local_iso_for(started),
                "elapsed_seconds": max(int((now - started).total_seconds()), 0),
                "server_calculated_at_utc": now.isoformat(),
            }
        )
    return sorted(sessions, key=lambda item: item["signed_in_at_utc"])


def live_roster_snapshot(transport: str = "websocket") -> dict:
    employees = active_sessions()
    guests = active_guest_sessions()
    roster = [
        {
            **session,
            "person_type": "employee",
            "session_id": session["employee_id"],
            "started_at_utc": session["clocked_in_at_utc"],
        }
        for session in employees
    ]
    roster.extend(
        {
            **session,
            "person_type": "guest",
            "session_id": session["guest_session_id"],
            "started_at_utc": session["signed_in_at_utc"],
            "current_status": "onsite",
            "requires_manager_review": False,
        }
        for session in guests
    )
    roster.sort(key=lambda item: item["started_at_utc"])
    return {
        "ok": True,
        "message_type": "live_roster",
        "active_sessions": employees,
        "active_guest_sessions": guests,
        "active_roster": roster,
        "active_employee_count": len(employees),
        "active_guest_count": len(guests),
        "active_session_count": len(roster),
        "server_calculated_at_utc": utc_now().isoformat(),
        "transport": transport,
        "poll_interval_seconds": 15,
    }


def kiosk_live_snapshot(transport: str = "websocket") -> dict:
    """Public kiosk state deliberately excludes names, IDs, hours, and session records."""
    return {
        "ok": True,
        "message_type": "kiosk_status",
        "active_employee_count": len(active_sessions()),
        "active_guest_count": len(active_guest_sessions()),
        "server_calculated_at_utc": utc_now().isoformat(),
        "transport": transport,
        "privacy": "anonymous_counts_only",
        "poll_interval_seconds": 15,
    }


def manager_summary(start: str | None = None, end: str | None = None) -> dict:
    period = reporting_range_contract(start, end)
    events = read_events(start, end)
    summaries = calc(events)
    live = live_roster_snapshot("http_polling_fallback")
    return {
        "ok": True,
        "range": {"start": start, "end": end},
        "reporting_period": period,
        "summaries": summaries,
        **{key: value for key, value in live.items() if key not in {"ok", "message_type"}},
        "completed_session_count": sum(1 for event in events if event.get("event_type") == "clock_out"),
        "total_hours": round(sum(float(row.get("net_work_hours", 0)) for row in summaries), 2),
        "source_ledger_hash": ledger_hash(),
        "setup_warnings": setup_warnings(),
        "export_routes": {
            "employee_csv": "/api/owner/export",
            "guest_csv": "/api/owner/guests/export",
        },
        "live_transport": {
            "mode": "websocket_with_http_polling_fallback",
            "websocket_port": LIVE_WEBSOCKET_STATE["port"],
            "poll_interval_seconds": 15,
            "server_authoritative": True,
            "websocket_or_sse_runtime_claimed": bool(LIVE_WEBSOCKET_STATE["available"]),
        },
        "non_claims": [
            "Hours and pay fields are estimates pending owner review.",
            "No payroll or tax compliance is claimed.",
        ],
    }


def guest_ledger_path() -> Path:
    now = utc_now()
    path = GUEST_LEDGER_DIR / f"{now.year:04d}" / f"{now.month:02d}" / f"guest_sessions_{now.year:04d}-{now.month:02d}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def append_guest_ledger_event(payload: dict) -> None:
    event = {**payload, "ledger_recorded_at_utc": utc_now().isoformat()}
    event["record_hash"] = sha_text(json.dumps(event, sort_keys=True, separators=(",", ":")))
    with guest_ledger_path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def guest_sign_in(guest_name: str, organization: str = "", purpose: str = "", notes: str = "") -> dict:
    name = str(guest_name).strip()
    if not name:
        raise ValueError("guest_name_required")
    now = utc_now().isoformat()
    session = {
        "guest_session_id": f"guest_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "guest_name": name,
        "organization": str(organization).strip(),
        "purpose": str(purpose).strip(),
        "sign_in_time_utc": now,
        "sign_out_time_utc": None,
        "notes": str(notes).strip(),
        "created_at_utc": now,
        "updated_at_utc": now,
    }
    db_execute(
        "INSERT INTO guest_sessions VALUES(?,?,?,?,?,?,?,?,?)",
        tuple(session.values()),
    )
    append_guest_ledger_event({"event_type": "guest_sign_in", **session})
    return session


def guest_sign_out(guest_session_id: str) -> dict:
    rows = db_rows("SELECT * FROM guest_sessions WHERE guest_session_id=?", (guest_session_id,))
    if not rows:
        raise ValueError("guest_session_not_found")
    session = rows[0]
    if session.get("sign_out_time_utc"):
        raise ValueError("guest_already_signed_out")
    now = utc_now().isoformat()
    db_execute(
        "UPDATE guest_sessions SET sign_out_time_utc=?,updated_at_utc=? WHERE guest_session_id=?",
        (now, now, guest_session_id),
    )
    session["sign_out_time_utc"] = now
    session["updated_at_utc"] = now
    append_guest_ledger_event({"event_type": "guest_sign_out", **session})
    return session


def guest_sign_out_by_name(guest_name: str, organization: str = "") -> dict:
    normalized_name = guest_name.strip().casefold()
    normalized_org = organization.strip().casefold()
    if not normalized_name:
        raise ValueError("guest_name_required")
    matches = [
        guest for guest in list_guest_sessions(False)
        if str(guest.get("guest_name", "")).strip().casefold() == normalized_name
        and (
            not normalized_org
            or str(guest.get("organization", "")).strip().casefold() == normalized_org
        )
    ]
    if not matches:
        raise ValueError("active_guest_not_found")
    if len(matches) > 1:
        raise ValueError("guest_name_ambiguous_add_organization")
    return guest_sign_out(str(matches[0]["guest_session_id"]))


def list_guest_sessions(include_closed: bool = True) -> list[dict]:
    if include_closed:
        return db_rows("SELECT * FROM guest_sessions ORDER BY sign_in_time_utc DESC")
    return db_rows("SELECT * FROM guest_sessions WHERE sign_out_time_utc IS NULL ORDER BY sign_in_time_utc")


def live_websocket_handler(connection) -> None:
    authenticated = False
    kiosk_connection = False
    try:
        request_path = str(getattr(getattr(connection, "request", None), "path", ""))
        if request_path.split("?", 1)[0] == "/kiosk/live":
            kiosk_connection = True
            with LIVE_CONNECTIONS_LOCK:
                KIOSK_CONNECTIONS.add(connection)
            connection.send(json.dumps(kiosk_live_snapshot("websocket")))
            for message in connection:
                if message == "ping":
                    connection.send("pong")
            return
        raw = connection.recv(timeout=10)
        message = json.loads(raw)
        authenticated = (
            message.get("type") == "authenticate"
            and verify_owner_token(message.get("owner_token"))
        )
        if not authenticated:
            connection.send(json.dumps({"ok": False, "error": "owner_token_invalid"}))
            connection.close(code=1008, reason="owner token required")
            return
        with LIVE_CONNECTIONS_LOCK:
            LIVE_CONNECTIONS.add(connection)
        connection.send(json.dumps(live_roster_snapshot("websocket")))
        for message in connection:
            if message == "ping":
                connection.send("pong")
    except (ConnectionClosed, TimeoutError, json.JSONDecodeError, TypeError):
        pass
    finally:
        if kiosk_connection:
            with LIVE_CONNECTIONS_LOCK:
                KIOSK_CONNECTIONS.discard(connection)
        if authenticated:
            with LIVE_CONNECTIONS_LOCK:
                LIVE_CONNECTIONS.discard(connection)


def broadcast_live_snapshot() -> None:
    payload = json.dumps(live_roster_snapshot("websocket"))
    kiosk_payload = json.dumps(kiosk_live_snapshot("websocket"))
    with LIVE_CONNECTIONS_LOCK:
        connections = list(LIVE_CONNECTIONS)
        kiosk_connections = list(KIOSK_CONNECTIONS)
    stale = []
    for connection in connections:
        try:
            connection.send(payload)
        except Exception:
            stale.append(connection)
    if stale:
        with LIVE_CONNECTIONS_LOCK:
            for connection in stale:
                LIVE_CONNECTIONS.discard(connection)
    kiosk_stale = []
    for connection in kiosk_connections:
        try:
            connection.send(kiosk_payload)
        except Exception:
            kiosk_stale.append(connection)
    if kiosk_stale:
        with LIVE_CONNECTIONS_LOCK:
            for connection in kiosk_stale:
                KIOSK_CONNECTIONS.discard(connection)


def start_live_websocket_server(host: str, port: int) -> dict:
    if websocket_serve is None:
        LIVE_WEBSOCKET_STATE.update(
            {"available": False, "host": host, "port": port, "error": "websockets_dependency_missing"}
        )
        return dict(LIVE_WEBSOCKET_STATE)

    ready = threading.Event()

    def run() -> None:
        try:
            with websocket_serve(
                live_websocket_handler,
                host,
                port,
                server_header=f"BestBudsTimeClock/{APP_VERSION}",
                ping_interval=20,
                ping_timeout=20,
            ) as server:
                LIVE_WEBSOCKET_STATE.update(
                    {"available": True, "host": host, "port": port, "error": None}
                )
                ready.set()
                server.serve_forever()
        except Exception as error:
            LIVE_WEBSOCKET_STATE.update(
                {"available": False, "host": host, "port": port, "error": str(error)}
            )
            ready.set()

    threading.Thread(target=run, name="bbtc-live-websocket", daemon=True).start()
    ready.wait(timeout=3)
    if not ready.is_set():
        LIVE_WEBSOCKET_STATE.update(
            {"available": False, "host": host, "port": port, "error": "startup_timeout"}
        )
    return dict(LIVE_WEBSOCKET_STATE)


def readable_local_datetime(value: str | None) -> str:
    parsed = parse_dt(value)
    return parsed and dt.datetime.fromisoformat(local_iso_for(parsed)).strftime("%Y-%m-%d %I:%M %p") or ""


def employee_session_export_rows(events: list[dict]) -> list[dict]:
    employees = employee_lookup()
    grouped: dict[str, list[dict]] = {}
    for event in events:
        grouped.setdefault(str(event["employee_id"]), []).append(event)
    manual_by_key: dict[tuple[str, str], list[dict]] = {}
    for adjustment in db_rows("SELECT * FROM manual_hours_adjustments ORDER BY work_date,created_at_utc"):
        manual_by_key.setdefault((adjustment["employee_id"], adjustment["work_date"]), []).append(adjustment)
    rows = []
    for employee_id, employee_events in grouped.items():
        employee = employees.get(employee_id, {})
        open_session = None
        break_started = None
        break_seconds = 0.0
        for event in sorted(employee_events, key=lambda item: (item["captured_at_utc"], item["event_id"])):
            event_time = parse_dt(event["captured_at_utc"])
            if event["event_type"] == "clock_in" and open_session is None:
                open_session = event_time
                break_started = None
                break_seconds = 0.0
            elif event["event_type"] == "break_start" and open_session and break_started is None:
                break_started = event_time
            elif event["event_type"] == "break_end" and break_started:
                break_seconds += max((event_time - break_started).total_seconds(), 0)
                break_started = None
            elif event["event_type"] == "clock_out" and open_session:
                if break_started:
                    break_seconds += max((event_time - break_started).total_seconds(), 0)
                    break_started = None
                local_start = dt.datetime.fromisoformat(local_iso_for(open_session))
                work_date = local_start.date().isoformat()
                adjustments = manual_by_key.get((employee_id, work_date), [])
                adjusted_hours = sum(float(item["hours"]) for item in adjustments)
                total_hours = max((event_time - open_session).total_seconds() / 3600 - break_seconds / 3600 + adjusted_hours, 0)
                rows.append(
                    human_employee_export_row(
                        employee_id, employee, work_date, open_session, event_time,
                        break_seconds, total_hours, adjustments,
                    )
                )
                open_session = None
                break_seconds = 0.0
        if open_session:
            now = utc_now()
            local_start = dt.datetime.fromisoformat(local_iso_for(open_session))
            work_date = local_start.date().isoformat()
            adjustments = manual_by_key.get((employee_id, work_date), [])
            adjusted_hours = sum(float(item["hours"]) for item in adjustments)
            active_break_seconds = break_seconds + (max((now - break_started).total_seconds(), 0) if break_started else 0)
            total_hours = max((now - open_session).total_seconds() / 3600 - active_break_seconds / 3600 + adjusted_hours, 0)
            rows.append(
                human_employee_export_row(
                    employee_id, employee, work_date, open_session, None,
                    active_break_seconds, total_hours, adjustments,
                )
            )
    return rows


def human_employee_export_row(
    employee_id: str,
    employee: dict,
    work_date: str,
    clock_in: dt.datetime,
    clock_out: dt.datetime | None,
    break_seconds: float,
    total_hours: float,
    adjustments: list[dict],
) -> dict:
    rate = float(employee.get("hourly_rate") or 0)
    gross = round(total_hours * rate, 2)
    tax_amount = float(employee.get("tax_withholding_amount") or 0)
    tax_percent = float(employee.get("tax_withholding_percent") or 0)
    tax = round(min(gross, tax_amount + gross * tax_percent / 100), 2)
    notes = [str(item["reason"]) for item in adjustments]
    if clock_out is None:
        notes.append("ACTIVE SESSION — totals continue changing")
    return {
        "Employee Name": employee.get("display_name", employee_id),
        "Employee ID": employee_id,
        "Date": work_date,
        "Clock In": readable_local_datetime(clock_in.isoformat()),
        "Clock Out": readable_local_datetime(clock_out.isoformat()) if clock_out else "OPEN",
        "Break Minutes": round(break_seconds / 60),
        "Total Hours": f"{total_hours:.2f}",
        "Hourly Rate": f"${rate:.2f}" if rate else "",
        "Gross Pay Estimate": f"${gross:.2f}" if rate else "",
        "Tax Withheld Estimate": f"${tax:.2f}" if rate else "",
        "Net Pay Estimate": f"${max(gross - tax, 0):.2f}" if rate else "",
        "Notes": "; ".join(notes),
    }


def guest_sessions_for_reporting_period(start: str | None = None, end: str | None = None) -> tuple[list[dict], dict]:
    period = reporting_range_contract(start, end)
    sessions = list_guest_sessions(True)
    if period["mode"] == "all_time":
        return sessions, period
    start_utc = parse_dt(period["start_utc"])
    end_exclusive_utc = parse_dt(period["end_exclusive_utc"])
    now = utc_now()
    filtered = []
    for session in sessions:
        signed_in = parse_dt(session.get("sign_in_time_utc"))
        signed_out = parse_dt(session.get("sign_out_time_utc")) or now
        if signed_in and signed_in < end_exclusive_utc and signed_out >= start_utc:
            filtered.append(session)
    return filtered, period


def export_guest_csv(start: str | None = None, end: str | None = None) -> Path:
    sessions, period = guest_sessions_for_reporting_period(start, end)
    range_tag = (
        f"{period['start_date']}_to_{period['end_date']}"
        if period["mode"] == "selected_period"
        else "all"
    )
    export_id = f"guest_export_{range_tag}_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:6]}"
    path = GUEST_EXPORT_DIR / f"{export_id}.csv"
    headers = ["Guest Name", "Organization", "Purpose", "Sign In", "Sign Out", "Visit Duration", "Notes"]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for session in sessions:
            started = parse_dt(session["sign_in_time_utc"])
            ended = parse_dt(session.get("sign_out_time_utc"))
            duration = ""
            if started and ended:
                minutes = max(int((ended - started).total_seconds() // 60), 0)
                duration = f"{minutes // 60}h {minutes % 60}m"
            writer.writerow(
                {
                    "Guest Name": session["guest_name"],
                    "Organization": session.get("organization") or "",
                    "Purpose": session.get("purpose") or "",
                    "Sign In": readable_local_datetime(session["sign_in_time_utc"]),
                    "Sign Out": readable_local_datetime(session.get("sign_out_time_utc")),
                    "Visit Duration": duration or "OPEN",
                    "Notes": session.get("notes") or "",
                }
            )
    write_audit_receipt({
        "receipt_type": "guest_csv_export",
        "export_file": path.name,
        "guest_count": len(sessions),
        "reporting_period": period,
        "selection_rule": "visit_overlaps_inclusive_local_business_dates",
    })
    return path


def local_network_ips() -> list[str]:
    import socket
    ips: set[str] = set()
    try:
        host = socket.gethostname()
        for item in socket.getaddrinfo(host, None):
            ip = item[4][0]
            if "." in ip and not ip.startswith("127."):
                ips.add(ip)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        if not ip.startswith("127."):
            ips.add(ip)
        s.close()
    except Exception:
        pass
    return sorted(ips)


def kiosk_employee_urls(host_header: str, port: int) -> dict:
    urls: list[str] = []
    seen: set[str] = set()
    for ip in local_network_ips():
        url = f"http://{ip}:{port}/employee"
        if url not in seen:
            seen.add(url)
            urls.append(url)
    if host_header:
        host_only = host_header.split(":")[0]
        for host in {host_header, host_only}:
            url = f"http://{host}:{port}/employee"
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return {
        "employee_path": "/employee",
        "urls": urls,
        "non_claims": [
            "QR and kiosk URLs are local-network entry helpers only.",
            "QR does not prove employee identity; PIN is still required.",
            "No hosted public deployment is implied.",
        ],
    }


def qr_svg_for_text(text: str, border: int = 4) -> str:
    from qrcodegen import QrCode
    qr = QrCode.encode_text(text, QrCode.Ecc.MEDIUM)
    size = qr.get_size()
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size + border * 2} {size + border * 2}" role="img" aria-label="QR code">',
        f'<rect width="100%" height="100%" fill="#fff"/>',
    ]
    for y in range(size):
        for x in range(size):
            if qr.get_module(x, y):
                parts.append(f'<rect x="{x + border}" y="{y + border}" width="1" height="1" fill="#0f172a"/>')
    parts.append("</svg>")
    return "".join(parts)


def punch_receipt(event: dict) -> dict:
    labels = {
        "clock_in": "Clock in accepted",
        "clock_out": "Clock out accepted",
        "break_start": "Break start accepted",
        "break_end": "Break end accepted",
    }
    accepted = event.get("validation_status") == "accepted"
    employee_id = str(event.get("employee_id", ""))
    if accepted:
        summary = employee_day_summary(employee_id)
        message = f"{labels.get(event.get('event_type'), 'Punch accepted')}. Today total: {summary['net_work_hours']:.2f} hours."
    else:
        summary = None
        message = "Punch rejected. Check employee ID, PIN, or employee status."
    return {
        "receipt_type": "employee_punch_receipt",
        "accepted": accepted,
        "message": message,
        "employee_id": employee_id,
        "event_id": event.get("event_id"),
        "event_type": event.get("event_type"),
        "event_label": labels.get(event.get("event_type"), str(event.get("event_type", "punch"))),
        "captured_local": event.get("captured_local"),
        "validation_status": event.get("validation_status"),
        "policy_flags": event.get("policy_flags", []),
        "today_summary": summary,
        "non_claims": [
            "Employee receipt is a UI/runtime acknowledgement, not payroll approval.",
            "Today hours are calculated from accepted ledger events available to this runtime."
        ]
    }


def ledger_hash() -> str:
    h = hashlib.sha256()
    for p in sorted(LEDGER_DIR.glob("**/*.jsonl")):
        h.update(p.read_bytes())
    return "sha256:" + h.hexdigest()


def append_event_to_ledger(ev: dict) -> dict:
    ev = dict(ev)
    ev.setdefault("prev_event_hash", last_hash())
    ev["event_hash"] = event_hash(ev)
    with ledger_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(ev, sort_keys=True) + "\n")
    csv_receipt = append_csv_ledger_mirror(ev)
    if not csv_receipt.get("ok"):
        ev.setdefault("mirror_warnings", []).append(csv_receipt.get("warning"))
    if ev.get("validation_status") == "accepted":
        db_execute(
            "INSERT INTO clock_events VALUES(?,?,?,?,?,?,?,?)",
            (
                ev["event_id"], ev["employee_id"], ev["event_type"], ev["captured_at_utc"],
                ev["captured_local"], ev["source"], ev["validation_status"], ev["event_hash"],
            ),
        )
    return ev


def create_owner_adjustment(employee_id: str, event_type: str, captured_at_utc: str, reason: str, owner_note: str = "") -> dict:
    cfg = settings()
    if not cfg.get("allow_owner_adjustments", True):
        raise ValueError("owner_adjustments_disabled")
    employee_id = str(employee_id).strip()
    event_type = str(event_type).strip()
    reason = str(reason).strip()
    if event_type not in EVENT_TYPES:
        raise ValueError("unsupported_adjustment_event_type")
    if not employee_id:
        raise ValueError("employee_id_required")
    if cfg.get("owner_adjustment_reason_required", True) and not reason:
        raise ValueError("adjustment_reason_required")
    if employee_id not in employee_lookup():
        raise ValueError("employee_not_found")
    adjusted_ts = parse_dt(captured_at_utc)
    if adjusted_ts is None:
        raise ValueError("captured_at_utc_required")
    created_at = utc_now().isoformat()
    adjustment_id = f"adj_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
    ev = {
        "event_id": f"clk_adjusted_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "employee_id": employee_id,
        "site_id": cfg["site_id"],
        "terminal_id": cfg["terminal_id"],
        "event_type": event_type,
        "captured_at_utc": adjusted_ts.isoformat(),
        "captured_local": local_iso_for(adjusted_ts),
        "local_timezone": cfg["timezone"],
        "source": "owner_adjustment",
        "auth_method": "owner_token",
        "validation_status": "accepted",
        "policy_flags": ["owner_adjustment", "requires_owner_review"],
        "notes": reason + ((" | " + str(owner_note).strip()) if str(owner_note).strip() else ""),
        "admin_adjustment": True,
        "owner_adjustment_id": adjustment_id,
        "prev_event_hash": last_hash(),
        "event_hash": "",
    }
    ev = append_event_to_ledger(ev)
    db_execute(
        "INSERT OR REPLACE INTO owner_adjustments VALUES(?,?,?,?,?,?,?,?,?)",
        (adjustment_id, ev["event_id"], employee_id, event_type, adjusted_ts.isoformat(), reason, owner_note, created_at, ev["event_hash"]),
    )
    receipt = write_audit_receipt({
        "receipt_type": "owner_adjustment",
        "adjustment_id": adjustment_id,
        "event_id": ev["event_id"],
        "employee_id": employee_id,
        "event_type": event_type,
        "adjusted_event_time_utc": adjusted_ts.isoformat(),
        "reason": reason,
        "owner_note": owner_note,
        "event_hash": ev["event_hash"],
    })
    return {"adjustment_id": adjustment_id, "event": ev, "receipt": receipt}


def owner_clock_out_live_person(person_type: str, session_id: str) -> dict:
    person_type = str(person_type).strip().lower()
    session_id = str(session_id).strip()
    if person_type == "employee":
        active = next(
            (session for session in active_sessions() if session["employee_id"] == session_id),
            None,
        )
        if active is None:
            raise ValueError("employee_not_currently_clocked_in")
        adjustment = create_owner_adjustment(
            session_id,
            "clock_out",
            utc_now().isoformat(),
            "owner live roster clock out",
            "Created from Timeclock Summary onsite card.",
        )
        return {
            "ok": True,
            "person_type": "employee",
            "display_name": active["display_name"],
            "employee_id": session_id,
            "action": "clock_out",
            "owner_adjustment": adjustment,
        }
    if person_type == "guest":
        active = next(
            (session for session in active_guest_sessions() if session["guest_session_id"] == session_id),
            None,
        )
        if active is None:
            raise ValueError("guest_not_currently_onsite")
        session = guest_sign_out(session_id)
        return {
            "ok": True,
            "person_type": "guest",
            "display_name": active["display_name"],
            "guest_session": session,
            "action": "sign_out",
        }
    raise ValueError("unsupported_person_type")


def offline_sync_receipts_dir() -> Path:
    p = OFFLINE_SYNC_DIR / "sync_receipts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def offline_batches_dir(kind: str) -> Path:
    p = OFFLINE_SYNC_DIR / kind
    p.mkdir(parents=True, exist_ok=True)
    return p


def sync_offline_batch(data: dict) -> dict:
    """Sync browser-side offline punch recovery evidence.

    Security posture: browser queue items deliberately do not persist employee PINs.
    Synced items are written to the canonical JSONL ledger with a pending-owner-review
    validation status, so they become audit evidence but do not silently become payroll-counted
    accepted time. Owner corrections/adjustments remain the payroll-counted path.
    """
    batch_id = str(data.get("offline_batch_id") or f"offline_batch_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}").strip()
    terminal_id = str(data.get("terminal_id") or settings()["terminal_id"]).strip()
    items = data.get("items") or []
    if not isinstance(items, list):
        raise ValueError("offline_items_must_be_list")
    if len(items) > 100:
        raise ValueError("offline_batch_too_large")
    accepted_pending = []
    rejected = []
    known = employee_lookup()
    cfg = settings()
    received_at_utc = utc_now().isoformat()
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            rejected.append({"index": idx, "error": "offline_item_not_object"})
            continue
        employee_id = str(item.get("employee_id", "")).strip()
        event_type = str(item.get("event_type", "")).strip()
        offline_event_id = str(item.get("offline_event_id") or f"offline_item_{idx}").strip()
        if event_type not in EVENT_TYPES:
            rejected.append({"offline_event_id": offline_event_id, "employee_id": employee_id, "error": "unsupported_event_type"})
            continue
        if employee_id not in known:
            rejected.append({"offline_event_id": offline_event_id, "employee_id": employee_id, "event_type": event_type, "error": "employee_not_found"})
            continue
        captured = item.get("captured_at_client_utc") or item.get("captured_at_utc") or received_at_utc
        try:
            captured_dt = parse_dt(str(captured)) or utc_now()
        except Exception:
            captured_dt = utc_now()
        ev = {
            "event_id": f"clk_offline_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}",
            "employee_id": employee_id,
            "site_id": cfg["site_id"],
            "terminal_id": terminal_id or cfg["terminal_id"],
            "event_type": event_type,
            "captured_at_utc": captured_dt.isoformat(),
            "captured_local": item.get("captured_local") or local_iso_for(captured_dt),
            "local_timezone": cfg["timezone"],
            "source": "offline_browser_queue",
            "auth_method": "offline_queue_no_pin_persisted",
            "validation_status": "offline_recovery_pending_owner_review",
            "policy_flags": ["offline_recovery", "pending_owner_review", "not_payroll_counted_until_owner_adjustment"],
            "notes": f"offline_event_id={offline_event_id}; batch_id={batch_id}; backend_received_at_utc={received_at_utc}",
            "admin_adjustment": False,
            "offline_event_id": offline_event_id,
            "offline_batch_id": batch_id,
            "backend_received_at_utc": received_at_utc,
            "prev_event_hash": last_hash(),
            "event_hash": "",
        }
        ev = append_event_to_ledger(ev)
        accepted_pending.append({
            "offline_event_id": offline_event_id,
            "canonical_event_id": ev["event_id"],
            "employee_id": employee_id,
            "event_type": event_type,
            "validation_status": ev["validation_status"],
            "event_hash": ev["event_hash"],
        })
    receipt = {
        "receipt_id": f"offline_sync_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "receipt_type": "offline_sync_receipt",
        "offline_batch_id": batch_id,
        "terminal_id": terminal_id,
        "received_at_utc": received_at_utc,
        "pending_review_count": len(accepted_pending),
        "rejected_count": len(rejected),
        "pending_review_items": accepted_pending,
        "rejected_items": rejected,
        "ledger_hash_after_sync": ledger_hash(),
        "csv_mirror_enabled": True,
        "non_claims": [
            "Offline browser queue is recovery evidence, not canonical payroll truth until synced and reviewed.",
            "Offline synced events are not counted as accepted payroll time until owner review/adjustment.",
            "Employee PINs are not persisted in browser storage by this offline queue."
        ]
    }
    receipt_json = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    receipt["receipt_hash"] = sha_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    rpath = offline_sync_receipts_dir() / f"{receipt['receipt_id']}.json"
    rpath.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    batch_path = offline_batches_dir("accepted_batches") / f"{batch_id}.json"
    batch_path.write_text(json.dumps({"request": data, "receipt": receipt}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "sync_status": "accepted_pending_owner_review" if accepted_pending else "no_pending_items_accepted",
        "offline_batch_id": batch_id,
        "pending_review_count": len(accepted_pending),
        "rejected_count": len(rejected),
        "pending_review_items": accepted_pending,
        "rejected_items": rejected,
        "receipt_file": rpath.name,
        "receipt": receipt,
    }


def list_offline_sync_receipts(limit: int = 50) -> list[dict]:
    out = []
    for p in sorted(offline_sync_receipts_dir().glob("*.json"), reverse=True)[:limit]:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data["receipt_file"] = p.name
            out.append(data)
        except Exception:
            continue
    return out


def read_all_events(start: str | None = None, end: str | None = None) -> list[dict]:
    start_dt = reporting_date_bound(start) if start and len(str(start)) == 10 else parse_dt(start)
    end_dt = (
        reporting_date_bound(end, True) - dt.timedelta(microseconds=1)
        if end and len(str(end)) == 10
        else parse_dt(end)
    )
    if start_dt and end_dt and start_dt > end_dt:
        raise ValueError("reporting_period_start_after_end")
    out = []
    for _p, _lineno, line in iter_ledger_lines():
        e = json.loads(line)
        ts = parse_dt(e.get("captured_at_utc"))
        if ts is None:
            continue
        if start_dt and ts < start_dt:
            continue
        if end_dt and ts > end_dt:
            continue
        out.append(e)
    return sorted(out, key=lambda e: (e.get("captured_at_utc", ""), e.get("event_id", "")))


def owner_review_report(start: str | None = None, end: str | None = None) -> dict:
    period = reporting_range_contract(start, end)
    events = read_all_events(start, end)
    accepted = [e for e in events if e.get("validation_status") == "accepted"]
    rejected = [e for e in events if e.get("validation_status") != "accepted"]
    adjustments = [e for e in accepted if e.get("admin_adjustment") is True or e.get("source") == "owner_adjustment"]
    summaries = calc(accepted)
    exceptions = collect_exceptions(summaries)
    flags = []
    if rejected:
        flags.append("rejected_punches_present")
    if adjustments:
        flags.append("owner_adjustments_present")
    if exceptions:
        flags.append("calculation_exceptions_present")
    return {
        "review_id": f"review_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "version": APP_VERSION,
        "generated_at_utc": utc_now().isoformat(),
        "start": start,
        "end": end,
        "reporting_period": period,
        "site_id": settings()["site_id"],
        "source_ledger_hash": ledger_hash(),
        "event_count": len(events),
        "accepted_event_count": len(accepted),
        "rejected_event_count": len(rejected),
        "owner_adjustment_count": len(adjustments),
        "summary_count": len(summaries),
        "exceptions": exceptions,
        "rejected_events": rejected,
        "owner_adjustments": adjustments,
        "totals": period_total_row(summaries),
        "review_flags": flags,
        "recommended_owner_actions": [
            "Review rejected punches before closing payroll." if rejected else "No rejected punches detected in selected range.",
            "Review owner adjustments and preserve reason notes." if adjustments else "No owner adjustments detected in selected range.",
            "Resolve open/duplicate calculation exceptions before final payroll." if exceptions else "No calculation exceptions detected in selected range.",
        ],
        "non_claims": [
            "manager review is an operational review report, not a legal compliance seal",
            "owner adjustments are audit-marked accepted events and should be reviewed before payroll close",
        ],
    }


def write_owner_review_report(start: str | None = None, end: str | None = None) -> Path:
    report = owner_review_report(start, end)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    p = EXPORT_DIR / f"{report['review_id']}.json"
    p.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_audit_receipt({"receipt_type": "manager_review_report", "review_id": report["review_id"], "path": p.name, "source_ledger_hash": report["source_ledger_hash"]})
    return p


def export(fmt: str, start: str | None = None, end: str | None = None) -> Path:
    s = settings()
    if fmt not in s.get("allowed_export_formats", ["csv", "json", "markdown", "html"]):
        raise ValueError("unsupported_export_format")
    period = reporting_range_contract(start, end)
    events = read_events(start, end)
    rows = calc(events)
    eid = f"export_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:6]}"
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "export_id": eid,
        "format": fmt,
        "start": start,
        "end": end,
        "reporting_period": period,
        "generated_at_utc": utc_now().isoformat(),
        "source_ledger_hash": ledger_hash(),
        "summary_count": len(rows),
        "event_count": len(events),
        "non_claims": ["overtime is an estimate until owner/payroll review", "export is not a legal compliance seal"],
    }
    if fmt == "json":
        p = EXPORT_DIR / f"{eid}.json"
        p.write_text(json.dumps({"manifest": manifest, "summaries": rows, "events": events}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif fmt == "csv":
        p = EXPORT_DIR / f"{eid}.csv"
        human_rows = employee_session_export_rows(events)
        headers = [
            "Employee Name", "Employee ID", "Date", "Clock In", "Clock Out",
            "Break Minutes", "Total Hours", "Hourly Rate", "Gross Pay Estimate",
            "Tax Withheld Estimate", "Net Pay Estimate", "Notes",
        ]
        with p.open("w", newline="", encoding="utf-8-sig") as f:
            wr = csv.DictWriter(f, fieldnames=headers)
            wr.writeheader()
            wr.writerows(human_rows)
        manifest["human_readable_row_count"] = len(human_rows)
        manifest["csv_headers"] = headers
    elif fmt == "markdown":
        p = EXPORT_DIR / f"{eid}.md"
        lines = [
            "# Owner Time Clock Export",
            "",
            f"- Export ID: `{eid}`",
            f"- Generated UTC: `{manifest['generated_at_utc']}`",
            f"- Ledger hash: `{ledger_hash()}`",
            f"- Range: `{start or 'ALL'}` to `{end or 'ALL'}`",
            "",
            "| Employee | Name | Gross | Break | Net | Regular est. | OT est. | Exceptions |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
        for r in rows:
            lines.append(
                f"| {r['employee_id']} | {r['display_name']} | {r['gross_work_hours']} | {r['break_hours']} | {r['net_work_hours']} | {r['regular_hours_estimate']} | {r['overtime_hours_estimate']} | {', '.join(r['exceptions']) or 'none'} |"
            )
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif fmt == "html":
        p = EXPORT_DIR / f"{eid}.html"
        body = "".join(
            f"<tr><td>{html.escape(r['employee_id'])}</td><td>{html.escape(r['display_name'])}</td><td>{r['gross_work_hours']}</td><td>{r['break_hours']}</td><td>{r['net_work_hours']}</td><td>{r['regular_hours_estimate']}</td><td>{r['overtime_hours_estimate']}</td><td>{html.escape(', '.join(r['exceptions']) or 'none')}</td></tr>"
            for r in rows
        )
        p.write_text(
            "<!doctype html><meta charset='utf-8'><title>Owner Time Clock Export</title>"
            f"<h1>Owner Time Clock Export</h1><p>Export ID: {html.escape(eid)}</p><p>Ledger hash: {html.escape(ledger_hash())}</p>"
            "<table border='1' cellpadding='6'><tr><th>Employee</th><th>Name</th><th>Gross</th><th>Break</th><th>Net</th><th>Regular est.</th><th>OT est.</th><th>Exceptions</th></tr>"
            + body
            + "</table>",
            encoding="utf-8",
        )
    else:
        raise ValueError("unsupported_export_format")
    manifest_path = EXPORT_DIR / f"{eid}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_audit_receipt({"receipt_type": "owner_export", **manifest, "path": str(p.name)})
    return p


def verify_owner_token(token: str | None) -> bool:
    expected = settings().get("owner_token", "")
    return bool(token) and hmac.compare_digest(str(token), str(expected))


def generate_owner_token() -> str:
    """Create a high-entropy, URL-safe owner token without persisting it."""
    return "bbtc_owner_" + secrets.token_urlsafe(32)


def local_computer_addresses() -> set[str]:
    addresses = {"127.0.0.1", "::1"}
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None):
            addresses.add(str(item[4][0]).split("%", 1)[0])
    except OSError:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        addresses.add(str(probe.getsockname()[0]))
        probe.close()
    except OSError:
        pass
    return addresses


def is_local_computer_address(value: str | None) -> bool:
    try:
        candidate = ipaddress.ip_address(str(value or "").split("%", 1)[0])
        if candidate.version == 6 and candidate.ipv4_mapped:
            candidate = candidate.ipv4_mapped
        if candidate.is_loopback:
            return True
        return any(
            candidate == ipaddress.ip_address(address)
            for address in local_computer_addresses()
        )
    except ValueError:
        return False


def write_settings_atomic(value: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = CONFIG_DIR / f".settings.{uuid.uuid4().hex}.tmp"
    try:
        temp_path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp_path, SETTINGS_PATH)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def owner_token_security_status(local_request: bool) -> dict:
    configured = settings().get("owner_token") != DEFAULT_OWNER_TOKEN
    if configured:
        action = "enter_current_token_to_rotate"
    elif local_request:
        action = "generate_initial_token"
    else:
        action = "open_owner_console_on_server_computer"
    return {
        "ok": True,
        "configured": configured,
        "setup_required": not configured,
        "local_request": bool(local_request),
        "can_generate": configured or bool(local_request),
        "current_token_required": configured,
        "action": action,
    }


def new_owner_backup_token_set() -> tuple[dict, list[str]]:
    generated_at = utc_now().isoformat()
    set_id = f"owner_backup_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
    plaintext_tokens = [
        "bbtc_backup_" + secrets.token_urlsafe(24)
        for _ in range(OWNER_BACKUP_TOKEN_COUNT)
    ]
    stored_set = {
        "set_id": set_id,
        "generated_at_utc": generated_at,
        "tokens": [
            {
                "backup_token_id": f"{set_id}_{index:02d}",
                "token_hash": sha_text(token),
                "used_at_utc": None,
            }
            for index, token in enumerate(plaintext_tokens, start=1)
        ],
    }
    return stored_set, plaintext_tokens


def generate_and_save_owner_token(current_token: str | None, allow_initial_setup: bool) -> dict:
    """Generate and atomically persist a token.

    Initial setup is authorized by the HTTP handler only for a request from the server
    computer. It creates the first recovery set in the same atomic settings update.
    Once configured, every rotation requires the current token.
    """
    with OWNER_TOKEN_UPDATE_LOCK:
        current_settings = load_json(SETTINGS_PATH, {})
        expected = str(current_settings.get("owner_token", DEFAULT_OWNER_TOKEN))
        first_time_setup = expected == DEFAULT_OWNER_TOKEN
        if first_time_setup:
            if not allow_initial_setup:
                raise PermissionError("owner_token_initial_setup_local_only")
        elif not current_token or not hmac.compare_digest(str(current_token), expected):
            raise PermissionError("owner_token_current_required_or_invalid")

        new_token = generate_owner_token()
        updated_at = utc_now().isoformat()
        current_settings["owner_token"] = new_token
        current_settings["owner_token_updated_at_utc"] = updated_at
        current_settings["owner_token_setup_method"] = "guided_generator"
        backup_set = None
        backup_tokens: list[str] = []
        if first_time_setup:
            backup_set, backup_tokens = new_owner_backup_token_set()
            current_settings["owner_backup_token_set"] = backup_set
        write_settings_atomic(current_settings)

        write_audit_receipt(
            {
                "receipt_type": "owner_token_initialized" if first_time_setup else "owner_token_rotated",
                "setup_method": "guided_generator",
            }
        )
        if first_time_setup and backup_set:
            write_audit_receipt(
                {
                    "receipt_type": "owner_backup_token_set_initialized",
                    "backup_set_id": backup_set["set_id"],
                    "backup_token_count": OWNER_BACKUP_TOKEN_COUNT,
                }
            )
        result = {
            "ok": True,
            "owner_token": new_token,
            "configured": True,
            "first_time_setup": first_time_setup,
            "updated_at_utc": updated_at,
            "shown_once": True,
        }
        if first_time_setup and backup_set:
            result.update(
                {
                    "backup_set_id": backup_set["set_id"],
                    "backup_tokens": backup_tokens,
                    "backup_token_count": OWNER_BACKUP_TOKEN_COUNT,
                    "backup_tokens_shown_once": True,
                    "previous_set_invalidated": False,
                    "recovery_file_ready": True,
                }
            )
        return result


def generate_owner_backup_tokens(current_token: str | None) -> dict:
    """Replace the recovery set and return ten plaintext tokens exactly once."""
    with OWNER_TOKEN_UPDATE_LOCK:
        current_settings = load_json(SETTINGS_PATH, {})
        expected = str(current_settings.get("owner_token", DEFAULT_OWNER_TOKEN))
        if expected == DEFAULT_OWNER_TOKEN:
            raise PermissionError("owner_token_setup_required")
        if not current_token or not hmac.compare_digest(str(current_token), expected):
            raise PermissionError("owner_token_current_required_or_invalid")

        stored_set, plaintext_tokens = new_owner_backup_token_set()
        set_id = stored_set["set_id"]
        generated_at = stored_set["generated_at_utc"]
        current_settings["owner_backup_token_set"] = stored_set
        write_settings_atomic(current_settings)
        write_audit_receipt(
            {
                "receipt_type": "owner_backup_token_set_replaced",
                "backup_set_id": set_id,
                "backup_token_count": OWNER_BACKUP_TOKEN_COUNT,
            }
        )
        return {
            "ok": True,
            "backup_set_id": set_id,
            "backup_tokens": plaintext_tokens,
            "backup_token_count": OWNER_BACKUP_TOKEN_COUNT,
            "generated_at_utc": generated_at,
            "shown_once": True,
            "previous_set_invalidated": True,
        }


def recover_owner_token(backup_token: str | None) -> dict:
    """Consume one unused backup token and issue a new owner token."""
    candidate = str(backup_token or "").strip()
    if not candidate:
        raise PermissionError("backup_token_required")
    candidate_hash = sha_text(candidate)
    with OWNER_TOKEN_UPDATE_LOCK:
        current_settings = load_json(SETTINGS_PATH, {})
        backup_set = current_settings.get("owner_backup_token_set") or {}
        token_records = backup_set.get("tokens") or []
        matched = None
        for record in token_records:
            stored_hash = str(record.get("token_hash", ""))
            if record.get("used_at_utc") is None and stored_hash and hmac.compare_digest(candidate_hash, stored_hash):
                matched = record
        if matched is None:
            raise PermissionError("backup_token_invalid_or_used")

        updated_at = utc_now().isoformat()
        new_token = generate_owner_token()
        matched["used_at_utc"] = updated_at
        current_settings["owner_token"] = new_token
        current_settings["owner_token_updated_at_utc"] = updated_at
        current_settings["owner_token_setup_method"] = "single_use_backup_recovery"
        write_settings_atomic(current_settings)
        remaining = sum(1 for record in token_records if record.get("used_at_utc") is None)
        write_audit_receipt(
            {
                "receipt_type": "owner_token_recovered",
                "backup_set_id": backup_set.get("set_id"),
                "backup_token_id": matched.get("backup_token_id"),
                "backup_tokens_remaining": remaining,
            }
        )
        return {
            "ok": True,
            "owner_token": new_token,
            "configured": True,
            "updated_at_utc": updated_at,
            "shown_once": True,
            "backup_token_consumed": True,
            "backup_tokens_remaining": remaining,
        }


def json_response(handler: BaseHTTPRequestHandler, code: int, payload, ctype="application/json"):
    body = (json.dumps(payload, indent=2, sort_keys=True) if isinstance(payload, (dict, list)) else str(payload)).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", ctype + "; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def safe_export_file(name: str) -> Path:
    name = Path(name).name
    p = (EXPORT_DIR / name).resolve()
    if EXPORT_DIR.resolve() not in p.parents and p != EXPORT_DIR.resolve():
        raise ValueError("invalid_export_path")
    if not p.exists() or not p.is_file():
        raise FileNotFoundError("export_file_not_found")
    return p


def safe_guest_export_file(name: str) -> Path:
    clean_name = Path(name).name
    path = (GUEST_EXPORT_DIR / clean_name).resolve()
    if GUEST_EXPORT_DIR.resolve() not in path.parents or not path.exists() or not path.is_file():
        raise FileNotFoundError("guest_export_file_not_found")
    return path


def safe_label(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    cleaned = re.sub(r"[^0-9A-Za-z_.-]+", "-", str(value).strip())
    return cleaned.strip("-") or fallback


def path_hash(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def write_json_artifact(path: Path, payload: dict | list) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path_hash(path)


def pay_period_year(start: str | None, end: str | None) -> str:
    candidate = start or end
    if candidate and len(candidate) >= 4 and candidate[:4].isdigit():
        return candidate[:4]
    return utc_now().strftime("%Y")


def period_total_row(rows: list[dict]) -> dict:
    return {
        "employee_count": len(rows),
        "gross_work_hours": round(sum(float(r.get("gross_work_hours", 0)) for r in rows), 2),
        "break_hours": round(sum(float(r.get("break_hours", 0)) for r in rows), 2),
        "net_work_hours": round(sum(float(r.get("net_work_hours", 0)) for r in rows), 2),
        "regular_hours_estimate": round(sum(float(r.get("regular_hours_estimate", 0)) for r in rows), 2),
        "overtime_hours_estimate": round(sum(float(r.get("overtime_hours_estimate", 0)) for r in rows), 2),
        "exception_count": sum(len(r.get("exceptions", [])) for r in rows),
    }


def collect_exceptions(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        for x in r.get("exceptions", []):
            out.append({"employee_id": r.get("employee_id"), "display_name": r.get("display_name"), "exception": x})
    return out


def write_payroll_summary_csv(path: Path, rows: list[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=[
            "employee_id", "display_name", "gross_work_hours", "break_hours", "net_work_hours",
            "regular_hours_estimate", "overtime_hours_estimate", "source_event_count", "exceptions"
        ])
        wr.writeheader()
        for r in rows:
            x = {k: r.get(k, "") for k in wr.fieldnames}
            x["exceptions"] = ";".join(r.get("exceptions", []))
            wr.writerow(x)
    return path_hash(path)


def write_owner_review_md(path: Path, manifest_seed: dict, rows: list[dict], exceptions: list[dict]) -> str:
    lines = [
        "# Closed Pay Period Owner Review",
        "",
        f"- Period ID: `{manifest_seed['period_id']}`",
        f"- Start: `{manifest_seed.get('start') or 'ALL'}`",
        f"- End: `{manifest_seed.get('end') or 'ALL'}`",
        f"- Closed UTC: `{manifest_seed['closed_at_utc']}`",
        f"- Source ledger hash: `{manifest_seed['source_ledger_hash']}`",
        "",
        "## Totals",
        "",
        f"- Employees: `{manifest_seed['totals']['employee_count']}`",
        f"- Gross hours: `{manifest_seed['totals']['gross_work_hours']}`",
        f"- Break hours: `{manifest_seed['totals']['break_hours']}`",
        f"- Net hours: `{manifest_seed['totals']['net_work_hours']}`",
        f"- Regular estimate: `{manifest_seed['totals']['regular_hours_estimate']}`",
        f"- Overtime estimate: `{manifest_seed['totals']['overtime_hours_estimate']}`",
        "",
        "## Employee Summary",
        "",
        "| Employee | Name | Gross | Break | Net | Regular est. | OT est. | Exceptions |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(f"| {r['employee_id']} | {r['display_name']} | {r['gross_work_hours']} | {r['break_hours']} | {r['net_work_hours']} | {r['regular_hours_estimate']} | {r['overtime_hours_estimate']} | {', '.join(r.get('exceptions', [])) or 'none'} |")
    lines += ["", "## Exceptions", ""]
    if exceptions:
        for e in exceptions:
            lines.append(f"- `{e['employee_id']}` / {e['display_name']}: `{e['exception']}`")
    else:
        lines.append("No calculation exceptions detected.")
    lines += ["", "## Non-claims", ""]
    for nc in manifest_seed["non_claims"]:
        lines.append(f"- {nc}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path_hash(path)


def write_payroll_summary_html(path: Path, manifest_seed: dict, rows: list[dict]) -> str:
    body = "".join(
        f"<tr><td>{html.escape(r['employee_id'])}</td><td>{html.escape(r['display_name'])}</td><td>{r['gross_work_hours']}</td><td>{r['break_hours']}</td><td>{r['net_work_hours']}</td><td>{r['regular_hours_estimate']}</td><td>{r['overtime_hours_estimate']}</td><td>{html.escape(', '.join(r.get('exceptions', [])) or 'none')}</td></tr>"
        for r in rows
    )
    path.write_text(
        "<!doctype html><meta charset='utf-8'><title>Closed Pay Period</title>"
        f"<h1>Closed Pay Period</h1><p>Period ID: {html.escape(manifest_seed['period_id'])}</p>"
        f"<p>Range: {html.escape(str(manifest_seed.get('start') or 'ALL'))} to {html.escape(str(manifest_seed.get('end') or 'ALL'))}</p>"
        f"<p>Source ledger hash: {html.escape(manifest_seed['source_ledger_hash'])}</p>"
        "<table border='1' cellpadding='6'><tr><th>Employee</th><th>Name</th><th>Gross</th><th>Break</th><th>Net</th><th>Regular est.</th><th>OT est.</th><th>Exceptions</th></tr>"
        + body + "</table>",
        encoding="utf-8",
    )
    return path_hash(path)


def make_zip_from_dir(src_dir: Path, zip_path: Path) -> str:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for item in sorted(src_dir.rglob("*")):
            if item.is_file() and item != zip_path:
                z.write(item, item.relative_to(src_dir))
    return path_hash(zip_path)


def close_pay_period(start: str | None, end: str | None, owner_note: str = "") -> dict:
    # Validate the inclusive local reporting period before writing closure artifacts.
    period = reporting_range_contract(start, end)
    events = read_events(start, end)
    summaries = calc(events)
    exceptions = collect_exceptions(summaries)
    closed_at = utc_now().isoformat()
    period_id = f"pp_{safe_label(start, 'all')}_to_{safe_label(end, 'all')}_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:6]}"
    period_dir = PAY_PERIOD_DIR / pay_period_year(start, end) / period_id
    period_dir.mkdir(parents=True, exist_ok=True)
    totals = period_total_row(summaries)
    review = owner_review_report(start, end)
    seed = {
        "period_id": period_id,
        "version": APP_VERSION,
        "start": start,
        "end": end,
        "reporting_period": period,
        "closed_at_utc": closed_at,
        "site_id": settings()["site_id"],
        "terminal_id": settings()["terminal_id"],
        "owner_note": owner_note,
        "source_ledger_hash": ledger_hash(),
        "event_count": len(events),
        "totals": totals,
        "file_hashes": {},
        "status": "closed_pending_owner_review",
        "manager_review": {
            "review_id": review["review_id"],
            "review_flags": review["review_flags"],
            "rejected_event_count": review["rejected_event_count"],
            "owner_adjustment_count": review["owner_adjustment_count"],
            "exception_count": len(review["exceptions"]),
        },
        "non_claims": [
            "pay-period close is an owner review artifact, not a legal compliance seal",
            "regular/overtime calculations are estimates until confirmed against company policy and applicable law",
            "source proof is limited to accepted JSONL clock events present at close time",
        ],
    }
    file_hashes = {}
    file_hashes["summaries.json"] = write_json_artifact(period_dir / "summaries.json", summaries)
    file_hashes["accepted_events.json"] = write_json_artifact(period_dir / "accepted_events.json", events)
    file_hashes["exceptions.json"] = write_json_artifact(period_dir / "exceptions.json", exceptions)
    file_hashes["manager_review_report.json"] = write_json_artifact(period_dir / "manager_review_report.json", review)
    file_hashes["payroll_summary.csv"] = write_payroll_summary_csv(period_dir / "payroll_summary.csv", summaries)
    file_hashes["owner_review.md"] = write_owner_review_md(period_dir / "owner_review.md", seed, summaries, exceptions)
    file_hashes["payroll_summary.html"] = write_payroll_summary_html(period_dir / "payroll_summary.html", seed, summaries)
    seed["file_hashes"] = file_hashes
    manifest_path = period_dir / "pay_period_manifest.json"
    manifest_hash = write_json_artifact(manifest_path, seed)
    seed["manifest_hash"] = manifest_hash
    # Rewrite manifest with self-hash recorded as external receipt field is impossible without recursive hash drift; keep manifest_hash in DB/response.
    archive_path = period_dir / f"{period_id}.zip"
    archive_hash = make_zip_from_dir(period_dir, archive_path)
    db_execute(
        "INSERT OR REPLACE INTO pay_period_closures VALUES(?,?,?,?,?,?,?,?,?)",
        (period_id, start, end, closed_at, str(manifest_path), str(archive_path), manifest_hash, seed["source_ledger_hash"], seed["status"]),
    )
    receipt = write_audit_receipt({
        "receipt_type": "pay_period_close",
        "period_id": period_id,
        "start": start,
        "end": end,
        "manifest_path": str(manifest_path),
        "archive_path": str(archive_path),
        "manifest_hash": manifest_hash,
        "archive_hash": archive_hash,
        "source_ledger_hash": seed["source_ledger_hash"],
        "totals": totals,
    })
    seed.update({
        "manifest_path": str(manifest_path),
        "archive_path": str(archive_path),
        "archive_hash": archive_hash,
        "receipt": receipt,
        "download_url": f"/api/owner/pay_period/download?period_id={period_id}&file={period_id}.zip&owner_token=OWNER_TOKEN",
    })
    return seed


def list_pay_periods() -> list[dict]:
    rows = db_rows("SELECT period_id,start,end,closed_at_utc,manifest_path,archive_path,manifest_hash,source_ledger_hash,status FROM pay_period_closures ORDER BY closed_at_utc DESC")
    if rows:
        return rows
    # Fallback for copied data folders where DB was not rebuilt.
    out = []
    for manifest in sorted(PAY_PERIOD_DIR.glob("**/pay_period_manifest.json")):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            out.append({
                "period_id": data.get("period_id"),
                "start": data.get("start"),
                "end": data.get("end"),
                "closed_at_utc": data.get("closed_at_utc"),
                "manifest_path": str(manifest),
                "archive_path": str(manifest.parent / f"{data.get('period_id')}.zip"),
                "manifest_hash": path_hash(manifest),
                "source_ledger_hash": data.get("source_ledger_hash"),
                "status": data.get("status", "closed_pending_owner_review"),
            })
        except Exception:
            continue
    return sorted(out, key=lambda r: r.get("closed_at_utc") or "", reverse=True)


def safe_pay_period_file(period_id: str, filename: str) -> Path:
    safe_period = safe_label(period_id, "")
    safe_name = Path(filename).name
    candidates = list(PAY_PERIOD_DIR.glob(f"**/{safe_period}/{safe_name}"))
    if not candidates:
        raise FileNotFoundError("pay_period_file_not_found")
    p = candidates[0].resolve()
    if PAY_PERIOD_DIR.resolve() not in p.parents:
        raise ValueError("invalid_pay_period_path")
    return p



def data_file_inventory(exclude_backup_and_restore: bool = True) -> list[dict]:
    files = []
    for item in sorted(DATA_DIR.rglob("*")):
        if not item.is_file():
            continue
        if exclude_backup_and_restore and (BACKUP_DIR in item.parents or RESTORE_DIR in item.parents):
            continue
        rel = str(item.relative_to(DATA_DIR)).replace("\\", "/")
        files.append({"relative_path": rel, "bytes": item.stat().st_size, "sha256": path_hash(item)})
    return files


def runtime_data_tree_hash(files: list[dict] | None = None) -> str:
    h = hashlib.sha256()
    for row in files or data_file_inventory(True):
        h.update(row["relative_path"].encode("utf-8"))
        h.update(row["sha256"].encode("utf-8"))
    return "sha256:" + h.hexdigest()


def create_runtime_backup() -> dict:
    ensure_dirs()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_id = f"backup_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
    backup_path = BACKUP_DIR / f"{backup_id}.zip"
    files = data_file_inventory(True)
    manifest = {
        "backup_id": backup_id,
        "version": APP_VERSION,
        "created_at_utc": utc_now().isoformat(),
        "site_id": settings()["site_id"],
        "file_count": len(files),
        "files": files,
        "data_tree_hash": runtime_data_tree_hash(files),
        "source_ledger_hash": ledger_hash(),
        "restore_policy": {
            "dry_run_required_before_apply": True,
            "apply_requires_operator_shell_action": True,
            "server_route_performs_apply": False
        },
        "non_claims": [
            "backup archive is a runtime data snapshot, not a legal compliance seal",
            "restore application must be performed deliberately by an operator after dry-run verification"
        ]
    }
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as z:
        for row in files:
            src = DATA_DIR / row["relative_path"]
            z.write(src, row["relative_path"])
        z.writestr("backup_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    receipt = write_audit_receipt({
        "receipt_type": "runtime_backup",
        "backup_id": backup_id,
        "path": str(backup_path),
        "backup_sha256": path_hash(backup_path),
        "data_tree_hash": manifest["data_tree_hash"],
        "source_ledger_hash": manifest["source_ledger_hash"],
        "file_count": len(files)
    })
    return {"backup_id": backup_id, "backup_file": str(backup_path), "backup_sha256": path_hash(backup_path), "manifest": manifest, "receipt": receipt}


def factory_reset_runtime(confirmation: str) -> dict:
    if str(confirmation).strip() != "RESET BBTC":
        raise ValueError("factory_reset_confirmation_invalid")
    with FACTORY_RESET_LOCK:
        before = {
            "employee_count": len(list_employees(True)),
            "clock_event_count": len(read_all_events()),
            "guest_session_count": len(list_guest_sessions(True)),
        }
        backup = create_runtime_backup()
        backup_path = Path(backup["backup_file"]).resolve()
        verification = verify_runtime_backup(backup_path)
        if not verification.get("ok"):
            raise RuntimeError("factory_reset_backup_verification_failed")

        for item in list(DATA_DIR.iterdir()):
            if item.resolve() == BACKUP_DIR.resolve():
                continue
            if item.is_dir():
                shutil.rmtree(item)
            elif item.exists():
                item.unlink()

        init_db()
        receipt = write_audit_receipt(
            {
                "receipt_type": "factory_reset_completed",
                "backup_id": backup["backup_id"],
                "backup_file": backup["backup_file"],
                "backup_sha256": backup["backup_sha256"],
                "reset_counts": before,
                "preserved": [
                    "verified pre-reset backup",
                    "owner token and recovery credentials",
                    "packaged employee seed configuration",
                ],
            }
        )
        return {
            "ok": True,
            "reset": "runtime_factory_reset",
            "reset_counts": before,
            "backup_id": backup["backup_id"],
            "backup_file": backup["backup_file"],
            "backup_sha256": backup["backup_sha256"],
            "backup_verified": True,
            "owner_security_preserved": True,
            "seed_employee_count": len(list_employees(True)),
            "receipt": receipt,
        }


def safe_backup_file(name_or_path: str) -> Path:
    raw = str(name_or_path or "").strip()
    if not raw:
        raise FileNotFoundError("backup_file_required")
    name = Path(raw).name
    p = (BACKUP_DIR / name).resolve()
    if BACKUP_DIR.resolve() not in p.parents and p != BACKUP_DIR.resolve():
        raise ValueError("invalid_backup_path")
    if not p.exists() or not p.is_file():
        raise FileNotFoundError("backup_file_not_found")
    return p


def verify_runtime_backup(backup_path: Path) -> dict:
    errors = []
    checked = []
    if not zipfile.is_zipfile(backup_path):
        return {"ok": False, "backup_file": str(backup_path), "errors": ["not_a_zipfile"]}
    with zipfile.ZipFile(backup_path) as z:
        names = z.namelist()
        if "backup_manifest.json" not in names:
            errors.append("backup_manifest_missing")
            manifest = {}
        else:
            manifest = json.loads(z.read("backup_manifest.json").decode("utf-8"))
        for name in names:
            norm = Path(name)
            if name.startswith("/") or ".." in norm.parts:
                errors.append(f"unsafe_zip_path:{name}")
        for row in manifest.get("files", []):
            rel = row.get("relative_path")
            if rel not in names:
                errors.append(f"missing_file:{rel}")
                continue
            actual = "sha256:" + hashlib.sha256(z.read(rel)).hexdigest()
            expected = row.get("sha256")
            if actual != expected:
                errors.append(f"sha_mismatch:{rel}")
            checked.append(rel)
        if manifest and len(checked) != int(manifest.get("file_count", -1)):
            errors.append("file_count_mismatch")
        if manifest:
            calc_tree = runtime_data_tree_hash(manifest.get("files", []))
            if calc_tree != manifest.get("data_tree_hash"):
                errors.append("data_tree_hash_mismatch")
    return {
        "ok": not errors,
        "backup_file": str(backup_path),
        "backup_sha256": path_hash(backup_path),
        "manifest": manifest,
        "checked_files": checked,
        "checked_file_count": len(checked),
        "errors": errors,
        "non_claims": ["backup verification does not apply restored data", "verification does not prove legal/payroll compliance"]
    }


def restore_dry_run(backup_path: Path, target_root: Path | None = None) -> dict:
    verify = verify_runtime_backup(backup_path)
    restore_id = f"restore_dry_run_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
    target = (target_root or RESTORE_DIR / restore_id).resolve()
    errors = list(verify.get("errors", []))
    extracted_files = []
    if verify.get("ok"):
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(backup_path) as z:
            for name in z.namelist():
                if name == "backup_manifest.json":
                    continue
                dest = (target / name).resolve()
                if target not in dest.parents and dest != target:
                    errors.append(f"unsafe_extract_target:{name}")
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(name))
                extracted_files.append(str(dest.relative_to(target)).replace("\\", "/"))
    receipt = {
        "restore_id": restore_id,
        "checked_at_utc": utc_now().isoformat(),
        "backup_file": str(backup_path),
        "target": str(target),
        "verify_ok": verify.get("ok") is True,
        "extracted_file_count": len(extracted_files),
        "errors": errors,
        "status": "pass" if not errors else "fail",
        "non_claims": [
            "restore dry-run extracted into a candidate folder only",
            "production data was not overwritten",
            "operator must review before any apply action"
        ]
    }
    (target / "restore_dry_run_receipt.json").parent.mkdir(parents=True, exist_ok=True)
    (target / "restore_dry_run_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_audit_receipt({"receipt_type": "restore_dry_run", **receipt})
    return receipt



def list_pilot_issues(status: str | None = None) -> list[dict]:
    init_db()
    if status:
        return db_rows("SELECT issue_id, severity, status, title, details, created_at_utc, updated_at_utc, payload_hash FROM pilot_issues WHERE status=? ORDER BY created_at_utc DESC", (status,))
    return db_rows("SELECT issue_id, severity, status, title, details, created_at_utc, updated_at_utc, payload_hash FROM pilot_issues ORDER BY created_at_utc DESC")


def create_pilot_issue(severity: str, title: str, details: str = "", status: str = "open") -> dict:
    init_db()
    severity = str(severity or "medium").strip().lower()
    status = str(status or "open").strip().lower()
    title = str(title or "").strip()
    details = str(details or "").strip()
    if severity not in {"low", "medium", "high", "blocking"}:
        raise ValueError("unsupported_pilot_issue_severity")
    if status not in {"open", "monitoring", "resolved", "deferred"}:
        raise ValueError("unsupported_pilot_issue_status")
    if not title:
        raise ValueError("pilot_issue_title_required")
    now = utc_now().isoformat()
    issue = {
        "issue_id": f"pilot_issue_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "severity": severity,
        "status": status,
        "title": title,
        "details": details,
        "created_at_utc": now,
        "updated_at_utc": now,
    }
    issue["payload_hash"] = sha_text(json.dumps(issue, sort_keys=True))
    db_execute(
        "INSERT INTO pilot_issues VALUES(?,?,?,?,?,?,?,?)",
        (issue["issue_id"], issue["severity"], issue["status"], issue["title"], issue["details"], issue["created_at_utc"], issue["updated_at_utc"], issue["payload_hash"]),
    )
    write_audit_receipt({"receipt_type": "pilot_issue_logged", **issue})
    return issue


def pilot_readiness_report() -> dict:
    init_db()
    warnings = setup_warnings()
    employees = list_employees(False)
    all_events = read_events()
    open_issues = [x for x in list_pilot_issues() if x.get("status") in {"open", "monitoring"}]
    blocking_issues = [x for x in open_issues if x.get("severity") == "blocking"]
    latest_backup = None
    backups = sorted(BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    if backups:
        latest_backup = {"path": str(backups[0]), "file": backups[0].name, "sha256": sha_file(backups[0]) if backups[0].exists() else None}
    checks = {
        "active_employee_present": len(employees) >= 1,
        "owner_token_changed_before_live_use": "owner_token_default_change_required" not in warnings,
        "pin_pepper_changed_before_live_use": "pin_pepper_default_change_required" not in warnings,
        "ledger_readable": isinstance(all_events, list),
        "pilot_issue_log_available": True,
        "no_blocking_pilot_issues": len(blocking_issues) == 0,
        "backup_available_for_pilot": latest_backup is not None,
        "employee_receipt_runtime_available": callable(punch_receipt),
        "pay_period_close_available": callable(close_pay_period),
    }
    hard_blockers = [k for k, v in checks.items() if not v and k in {"active_employee_present", "ledger_readable", "pilot_issue_log_available", "no_blocking_pilot_issues"}]
    operator_warnings = [k for k, v in checks.items() if not v and k not in hard_blockers]
    if hard_blockers:
        status = "blocked"
    elif warnings or operator_warnings or open_issues:
        status = "ready_with_warnings"
    else:
        status = "ready"
    report = {
        "report_type": "live_pilot_readiness_report",
        "version": APP_VERSION,
        "status": status,
        "checked_at_utc": utc_now().isoformat(),
        "site_id": settings()["site_id"],
        "active_employee_count": len(employees),
        "accepted_event_count": len([e for e in all_events if e.get("validation_status") == "accepted"]),
        "open_issue_count": len(open_issues),
        "blocking_issue_count": len(blocking_issues),
        "checks": checks,
        "setup_warnings": warnings,
        "operator_warnings": operator_warnings,
        "hard_blockers": hard_blockers,
        "latest_backup": latest_backup,
        "source_ledger_hash": ledger_hash(),
        "non_claims": [
            "Pilot readiness is an operator acceptance aid, not a production deployment seal.",
            "Pilot readiness is not a legal, payroll, cannabis regulatory, or security compliance certification.",
            "Default owner token and PIN pepper warnings must be resolved before real live use."
        ],
    }
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    (PILOT_DIR / "latest_pilot_readiness_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_audit_receipt({"receipt_type": "pilot_readiness_report", **report})
    return report


def create_pilot_signoff(signer_name: str, signoff_role: str, decision: str, notes: str = "") -> dict:
    init_db()
    signer_name = str(signer_name or "").strip()
    signoff_role = str(signoff_role or "owner").strip().lower()
    decision = str(decision or "pilot_ready_with_warnings").strip().lower()
    notes = str(notes or "").strip()
    if not signer_name:
        raise ValueError("signer_name_required")
    if signoff_role not in {"owner", "manager", "operator", "payroll_reviewer"}:
        raise ValueError("unsupported_signoff_role")
    if decision not in {"pilot_ready", "pilot_ready_with_warnings", "pilot_blocked", "defer"}:
        raise ValueError("unsupported_pilot_decision")
    readiness = pilot_readiness_report()
    now = utc_now().isoformat()
    receipt = {
        "signoff_id": f"pilot_signoff_{utc_now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "signoff_role": signoff_role,
        "signer_name": signer_name,
        "decision": decision,
        "notes": notes,
        "created_at_utc": now,
        "readiness_status": readiness.get("status"),
    }
    receipt["payload_hash"] = sha_text(json.dumps(receipt, sort_keys=True))
    db_execute(
        "INSERT INTO pilot_signoffs VALUES(?,?,?,?,?,?,?,?)",
        (receipt["signoff_id"], receipt["signoff_role"], receipt["signer_name"], receipt["decision"], receipt["notes"], receipt["created_at_utc"], receipt["readiness_status"], receipt["payload_hash"]),
    )
    write_audit_receipt({"receipt_type": "pilot_signoff", **receipt})
    return receipt


def list_pilot_signoffs() -> list[dict]:
    init_db()
    return db_rows("SELECT signoff_id, signoff_role, signer_name, decision, notes, created_at_utc, readiness_status, payload_hash FROM pilot_signoffs ORDER BY created_at_utc DESC")


def create_pilot_acceptance_pack(owner_note: str = "") -> dict:
    init_db()
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    pack_id = f"pilot_acceptance_pack_{stamp}_{uuid.uuid4().hex[:8]}"
    out_dir = PILOT_DIR / pack_id
    out_dir.mkdir(parents=True, exist_ok=True)
    readiness = pilot_readiness_report()
    issues = list_pilot_issues()
    signoffs = list_pilot_signoffs()
    employee_card = """# Employee Time Clock Quick Start\n\n1. Enter your Employee ID.\n2. Enter your PIN.\n3. Tap Clock In, Clock Out, Start Break, or End Break.\n4. Wait for the green success receipt before walking away.\n5. If the screen rejects the punch or your hours look wrong, tell the owner/manager before leaving.\n\nBoundary: the receipt confirms the punch was recorded by this runtime; it is not payroll approval.\n"""
    owner_checklist = """# Owner Live Pilot Checklist\n\n- Change the default owner token.\n- Change the default PIN pepper.\n- Confirm every active employee has a correct Employee ID and PIN.\n- Run a backup and backup verification before pilot use.\n- Run the pilot readiness report.\n- Log issues during the pilot instead of editing raw ledger files.\n- Close the first pilot pay period only after manager review.\n"""
    files = {
        "pilot_readiness_report.json": readiness,
        "pilot_issues.json": issues,
        "pilot_signoffs.json": signoffs,
        "employee_quick_start.md": employee_card,
        "owner_live_pilot_checklist.md": owner_checklist,
        "pilot_owner_note.md": f"# Pilot Owner Note\n\n{owner_note or 'No owner note supplied.'}\n",
    }
    for name, value in files.items():
        if isinstance(value, str):
            (out_dir / name).write_text(value, encoding="utf-8")
        else:
            (out_dir / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_files = []
    for fp in sorted(out_dir.iterdir()):
        if fp.is_file():
            manifest_files.append({"file": fp.name, "bytes": fp.stat().st_size, "sha256": sha_file(fp)})
    manifest = {
        "manifest_type": "live_pilot_acceptance_pack_manifest",
        "pack_id": pack_id,
        "version": APP_VERSION,
        "created_at_utc": utc_now().isoformat(),
        "status": readiness.get("status"),
        "source_ledger_hash": ledger_hash(),
        "files": manifest_files,
        "non_claims": readiness.get("non_claims", []),
    }
    (out_dir / "pilot_acceptance_pack_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    archive = out_dir / f"{pack_id}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for fp in sorted(out_dir.iterdir()):
            if fp.is_file() and fp.name != archive.name:
                z.write(fp, fp.name)
    result = {
        "ok": True,
        "pack_id": pack_id,
        "status": readiness.get("status"),
        "pack_dir": str(out_dir),
        "archive_file": archive.name,
        "archive_path": str(archive),
        "archive_sha256": sha_file(archive),
        "download_url": f"/api/owner/pilot/download?pack_id={pack_id}&file={archive.name}&owner_token=OWNER_TOKEN",
    }
    write_audit_receipt({"receipt_type": "pilot_acceptance_pack", **result})
    return result


def safe_pilot_file(pack_id: str, filename: str) -> Path:
    if not re.match(r"^[A-Za-z0-9_.-]+$", str(pack_id)) or not re.match(r"^[A-Za-z0-9_.-]+$", str(filename)):
        raise ValueError("unsafe_pilot_file_request")
    p = (PILOT_DIR / pack_id / filename).resolve()
    if not str(p).startswith(str(PILOT_DIR.resolve())) or not p.exists() or not p.is_file():
        raise FileNotFoundError(filename)
    return p


STATIC_ASSETS = {
    "/static/app.js": ("app.js", "application/javascript"),
    "/static/style.css": ("style.css", "text/css"),
    "/static/offline_queue.js": ("offline_queue.js", "application/javascript"),
    "/static/employee.js": ("employee.js", "application/javascript"),
    "/static/kiosk_link.js": ("kiosk_link.js", "application/javascript"),
    "/static/kiosk_poster.js": ("kiosk_poster.js", "application/javascript"),
    "/static/hemp-bud-mark.svg": ("hemp-bud-mark.svg", "image/svg+xml"),
}


class Handler(BaseHTTPRequestHandler):
    server_version = "BestBudsTimeClock/0.7.0"

    def send_json(self, code: int, payload):
        return json_response(self, code, payload)

    def payload(self) -> dict:
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")) or 0).decode("utf-8")
        return json.loads(raw or "{}")

    def owner_token_from(self, query: dict | None = None, payload: dict | None = None) -> str | None:
        if payload and payload.get("owner_token"):
            return str(payload.get("owner_token"))
        if query and query.get("owner_token"):
            return str(query.get("owner_token", [""])[0])
        return self.headers.get("X-Owner-Token")

    def require_owner(self, query: dict | None = None, payload: dict | None = None) -> bool:
        if verify_owner_token(self.owner_token_from(query, payload)):
            return True
        self.send_json(403, {"error": "owner_token_invalid"})
        return False

    def is_local_computer_request(self) -> bool:
        return is_local_computer_address(str(self.client_address[0]))

    def do_GET(self):
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        if parsed.path == "/":
            return json_response(self, 200, (STATIC_DIR / "index.html").read_text(encoding="utf-8"), "text/html")
        if parsed.path == "/employee":
            return json_response(self, 200, (STATIC_DIR / "employee.html").read_text(encoding="utf-8"), "text/html")
        if parsed.path == "/kiosk-poster":
            return json_response(self, 200, (STATIC_DIR / "kiosk_poster.html").read_text(encoding="utf-8"), "text/html")
        if parsed.path in STATIC_ASSETS:
            name, ctype = STATIC_ASSETS[parsed.path]
            return json_response(self, 200, (STATIC_DIR / name).read_text(encoding="utf-8"), ctype)
        if parsed.path == "/api/kiosk/qr.svg":
            try:
                text = q.get("url", [""])[0]
                if not text:
                    return self.send_json(400, {"error": "url_required"})
                svg = qr_svg_for_text(text)
                return json_response(self, 200, svg, "image/svg+xml")
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/config/kiosk_urls":
            host = self.headers.get("Host", "127.0.0.1:8080")
            port = 8080
            if ":" in host:
                try:
                    port = int(host.rsplit(":", 1)[1])
                except ValueError:
                    port = 8080
            return self.send_json(200, kiosk_employee_urls(host, port))
        if parsed.path == "/api/health":
            return self.send_json(200, {
                "ok": True,
                "version": APP_VERSION,
                "setup_warnings": setup_warnings(),
                "site_id": settings()["site_id"],
                "websocket": dict(LIVE_WEBSOCKET_STATE),
            })
        if parsed.path == "/api/kiosk/status":
            return self.send_json(200, kiosk_live_snapshot("http_polling_fallback"))
        if parsed.path == "/api/config/public":
            s = settings()
            return self.send_json(200, {"version": APP_VERSION, "site_id": s["site_id"], "site_display_name": s["site_display_name"], "terminal_id": s["terminal_id"], "clock_events": sorted(EVENT_TYPES), "setup_warnings": setup_warnings()})
        if parsed.path == "/api/security/owner-token/status":
            return self.send_json(200, owner_token_security_status(self.is_local_computer_request()))
        if parsed.path == "/api/owner/summary":
            if not self.require_owner(q):
                return
            return self.send_json(200, manager_summary(q.get("start", [None])[0], q.get("end", [None])[0]))
        if parsed.path == "/api/owner/active-sessions":
            if not self.require_owner(q):
                return
            return self.send_json(200, live_roster_snapshot("http_polling_fallback"))
        if parsed.path == "/api/guests/active":
            return self.send_json(200, {
                "ok": True,
                "active_guest_count": len(active_guest_sessions()),
                "server_calculated_at_utc": utc_now().isoformat(),
                "privacy": "anonymous_count_only",
            })
        if parsed.path == "/api/owner/employees":
            if not self.require_owner(q):
                return
            return self.send_json(200, {"ok": True, "employees": list_employees(True)})
        if parsed.path == "/api/owner/guests":
            if not self.require_owner(q):
                return
            return self.send_json(200, {"ok": True, "guest_sessions": list_guest_sessions(True)})
        if parsed.path == "/api/owner/pay_periods":
            if not self.require_owner(q):
                return
            return self.send_json(200, {"pay_periods": list_pay_periods()})
        if parsed.path == "/api/owner/review":
            if not self.require_owner(q):
                return
            return self.send_json(200, owner_review_report(q.get("start", [None])[0], q.get("end", [None])[0]))
        if parsed.path == "/api/owner/pilot/issues":
            if not self.require_owner(q):
                return
            return self.send_json(200, {"issues": list_pilot_issues(q.get("status", [None])[0])})
        if parsed.path == "/api/owner/pilot/signoffs":
            if not self.require_owner(q):
                return
            return self.send_json(200, {"signoffs": list_pilot_signoffs()})
        if parsed.path == "/api/owner/offline/sync_receipts":
            if not self.require_owner(q):
                return
            return self.send_json(200, {"ok": True, "offline_sync_receipts": list_offline_sync_receipts()})
        if parsed.path == "/api/owner/pilot/download":
            if not self.require_owner(q):
                return
            try:
                p = safe_pilot_file(q.get("pack_id", [""])[0], q.get("file", [""])[0])
                body = p.read_bytes()
                ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Disposition", f"attachment; filename={p.name}")
                self.end_headers()
                self.wfile.write(body)
                return
            except Exception as e:
                return self.send_json(404, {"error": str(e)})
        if parsed.path == "/api/owner/pay_period/download":
            if not self.require_owner(q):
                return
            try:
                p = safe_pay_period_file(q.get("period_id", [""])[0], q.get("file", [""])[0])
                body = p.read_bytes()
                ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Disposition", f"attachment; filename={p.name}")
                self.end_headers()
                self.wfile.write(body)
                return
            except Exception as e:
                return self.send_json(404, {"error": str(e)})
        if parsed.path == "/api/owner/download":
            if not self.require_owner(q):
                return
            try:
                p = safe_export_file(q.get("file", [""])[0])
                body = p.read_bytes()
                ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Disposition", f"attachment; filename={p.name}")
                self.end_headers()
                self.wfile.write(body)
                return
            except Exception as e:
                return self.send_json(404, {"error": str(e)})
        if parsed.path == "/api/owner/guests/download":
            if not self.require_owner(q):
                return
            try:
                p = safe_guest_export_file(q.get("file", [""])[0])
                body = p.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Disposition", f"attachment; filename={p.name}")
                self.end_headers()
                self.wfile.write(body)
                return
            except Exception as e:
                return self.send_json(404, {"error": str(e)})
        return self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/security/owner-token/generate":
            try:
                data = self.payload()
                result = generate_and_save_owner_token(
                    self.owner_token_from(payload=data),
                    allow_initial_setup=self.is_local_computer_request(),
                )
                return self.send_json(200, result)
            except PermissionError as e:
                return self.send_json(403, {"ok": False, "error": str(e)})
            except Exception as e:
                return self.send_json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/security/backup-tokens/generate":
            try:
                data = self.payload()
                result = generate_owner_backup_tokens(self.owner_token_from(payload=data))
                return self.send_json(200, result)
            except PermissionError as e:
                return self.send_json(403, {"ok": False, "error": str(e)})
            except Exception as e:
                return self.send_json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/security/backup-tokens/recover":
            try:
                data = self.payload()
                result = recover_owner_token(data.get("backup_token"))
                return self.send_json(200, result)
            except PermissionError as e:
                return self.send_json(403, {"ok": False, "error": str(e)})
            except Exception as e:
                return self.send_json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/clock":
            try:
                data = self.payload()
                source = str(data.get("source", "web_index")).strip() or "web_index"
                ev = record(str(data.get("employee_id", "")).strip(), str(data.get("pin", "")).strip(), str(data.get("event_type", "")).strip(), source=source)
                receipt = punch_receipt(ev)
                if ev["validation_status"] == "accepted":
                    broadcast_live_snapshot()
                return self.send_json(200 if ev["validation_status"] == "accepted" else 403, {"ok": ev["validation_status"] == "accepted", "event": ev, "punch_receipt": receipt})
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/employee/summary":
            try:
                data = self.payload()
                result = employee_summary_auth(str(data.get("employee_id", "")).strip(), str(data.get("pin", "")).strip())
                status = 200 if result.get("ok") else 403
                return self.send_json(status, result)
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/guests/sign-in":
            try:
                data = self.payload()
                session = guest_sign_in(
                    str(data.get("guest_name", "")),
                    str(data.get("organization", "")),
                    str(data.get("purpose", "")),
                    str(data.get("notes", "")),
                )
                broadcast_live_snapshot()
                return self.send_json(200, {"ok": True, "guest_session": session})
            except Exception as e:
                return self.send_json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/guests/sign-out":
            try:
                data = self.payload()
                guest_session_id = str(data.get("guest_session_id", "")).strip()
                session = (
                    guest_sign_out(guest_session_id)
                    if guest_session_id
                    else guest_sign_out_by_name(
                        str(data.get("guest_name", "")),
                        str(data.get("organization", "")),
                    )
                )
                broadcast_live_snapshot()
                return self.send_json(200, {"ok": True, "guest_session": session})
            except Exception as e:
                return self.send_json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/offline/sync":
            try:
                data = self.payload()
                result = sync_offline_batch(data)
                return self.send_json(200, result)
            except Exception as e:
                return self.send_json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/owner/export":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                p = export(str(data.get("format", "csv")), data.get("start"), data.get("end"))
                return self.send_json(200, {"ok": True, "export_file": p.name, "download_url": f"/api/owner/download?file={p.name}&owner_token=OWNER_TOKEN", "source_ledger_hash": ledger_hash()})
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/owner/employees":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                employee = upsert_employee(
                    str(data.get("employee_id", "")).strip(),
                    str(data.get("display_name", "")).strip(),
                    str(data.get("pin", "")).strip(),
                    str(data.get("status", "active")).strip(),
                    str(data.get("role", "employee")).strip(),
                    data.get("hourly_rate"),
                    data.get("tax_withholding_amount"),
                    data.get("tax_withholding_percent"),
                )
                return self.send_json(200, {"ok": True, "employee": employee})
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/owner/employees/status":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                employee = set_employee_status(
                    str(data.get("employee_id", "")).strip(),
                    str(data.get("status", "")).strip(),
                )
                return self.send_json(200, {"ok": True, "employee": employee})
            except Exception as e:
                return self.send_json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/owner/employees/delete":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                result = permanently_delete_employee(
                    str(data.get("employee_id", "")).strip(),
                    str(data.get("confirmation", "")),
                )
                return self.send_json(200, result)
            except Exception as e:
                return self.send_json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/owner/manual-hours":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                adjustment = add_manual_hours(
                    str(data.get("employee_id", "")).strip(),
                    str(data.get("work_date", "")).strip(),
                    data.get("hours"),
                    str(data.get("reason", "")).strip(),
                )
                return self.send_json(200, {"ok": True, "manual_hours_adjustment": adjustment})
            except Exception as e:
                return self.send_json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/owner/live/clock-out":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                result = owner_clock_out_live_person(
                    str(data.get("person_type", "")),
                    str(data.get("session_id", "")),
                )
                broadcast_live_snapshot()
                result["live_roster"] = live_roster_snapshot("http_polling_fallback")
                return self.send_json(200, result)
            except Exception as e:
                return self.send_json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/owner/guests/export":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                start = data.get("start")
                end = data.get("end")
                period = reporting_range_contract(start, end)
                path = export_guest_csv(start, end)
                sessions, _period = guest_sessions_for_reporting_period(start, end)
                return self.send_json(
                    200,
                    {
                        "ok": True,
                        "export_file": path.name,
                        "download_url": f"/api/owner/guests/download?file={path.name}&owner_token=OWNER_TOKEN",
                        "guest_count": len(sessions),
                        "reporting_period": period,
                        "selection_rule": "visit_overlaps_inclusive_local_business_dates",
                    },
                )
            except Exception as e:
                return self.send_json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/owner/pay_period/close":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                result = close_pay_period(data.get("start"), data.get("end"), str(data.get("owner_note", "")))
                return self.send_json(200, {"ok": True, "pay_period": result})
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/owner/adjustment":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                result = create_owner_adjustment(
                    str(data.get("employee_id", "")).strip(),
                    str(data.get("event_type", "")).strip(),
                    str(data.get("captured_at_utc", "")).strip(),
                    str(data.get("reason", "")).strip(),
                    str(data.get("owner_note", "")).strip(),
                )
                return self.send_json(200, {"ok": True, "adjustment": result})
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/owner/pilot/readiness":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                return self.send_json(200, {"ok": True, "readiness": pilot_readiness_report()})
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/owner/pilot/issue":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                issue = create_pilot_issue(str(data.get("severity", "medium")), str(data.get("title", "")), str(data.get("details", "")), str(data.get("status", "open")))
                return self.send_json(200, {"ok": True, "issue": issue})
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/owner/pilot/signoff":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                receipt = create_pilot_signoff(str(data.get("signer_name", "")), str(data.get("signoff_role", "owner")), str(data.get("decision", "pilot_ready_with_warnings")), str(data.get("notes", "")))
                return self.send_json(200, {"ok": True, "signoff": receipt})
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/owner/pilot/package":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                result = create_pilot_acceptance_pack(str(data.get("owner_note", "")))
                return self.send_json(200, {"ok": True, "pilot_package": result})
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/owner/backup":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                backup = create_runtime_backup()
                return self.send_json(200, {"ok": True, **backup})
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/owner/backup/verify":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                p = safe_backup_file(str(data.get("backup_file", "")))
                verify = verify_runtime_backup(p)
                dry_run = restore_dry_run(p) if data.get("restore_dry_run", True) else None
                return self.send_json(200 if verify.get("ok") else 400, {"ok": verify.get("ok") is True and (dry_run is None or dry_run.get("status") == "pass"), "verify": verify, "restore_dry_run": dry_run})
            except Exception as e:
                return self.send_json(400, {"error": str(e)})
        if parsed.path == "/api/owner/factory-reset":
            try:
                data = self.payload()
                if not self.require_owner(payload=data):
                    return
                if not self.is_local_computer_request():
                    return self.send_json(403, {"ok": False, "error": "factory_reset_local_computer_only"})
                result = factory_reset_runtime(str(data.get("confirmation", "")))
                broadcast_live_snapshot()
                result["live_roster"] = live_roster_snapshot("http_polling_fallback")
                return self.send_json(200, result)
            except Exception as e:
                return self.send_json(400, {"ok": False, "error": str(e)})
        return self.send_json(404, {"error": "not_found"})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()
    init_db()
    websocket_state = start_live_websocket_server(args.host, args.port + 1)
    print(f"Best Buds Time Clock v{APP_VERSION} listening on http://{args.host}:{args.port}", flush=True)
    if websocket_state["available"]:
        print(f"Owner live WebSocket listening on ws://{args.host}:{args.port + 1}", flush=True)
    else:
        print(f"Owner live WebSocket unavailable; HTTP polling fallback active: {websocket_state['error']}", flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()

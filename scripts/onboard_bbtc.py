#!/usr/bin/env python3
"""Guided + live-verifying onboarding for the Best Buds Time Clock app.

One program, two audiences:

* Human operator (default): an interactive, readable walkthrough that checks the
  environment, surfaces the one true setup step (changing the default secrets), then
  optionally proves the app works by exercising the clock lifecycle against a live
  ephemeral server, and finally prints the "start the real server" gold path.
* LLM agent (``--agent`` / ``--json``): the same phases emitted as one canonical JSON
  object with an ``overall_status`` and a process exit code (0 pass / 1 fail).

Live verification is safe: it copies the app into a temporary directory and serves it on
``127.0.0.1`` on a free port, so the operator's real runtime ledger is never touched.

This script is additive. It does not modify ``server.py`` domain logic, adds no
third-party dependencies, and makes no production/deployment/payroll/compliance claim.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "repo_scaffold" / "app"
SETTINGS_PATH = APP / "config" / "settings.json"
SEED_PATH = APP / "config" / "employees.seed.json"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "unknown"

DEFAULT_OWNER_TOKEN = "CHANGE_ME_OWNER_TOKEN"
DEFAULT_PIN_PEPPER = "CHANGE_ME_PIN_PEPPER"
SEED_EMPLOYEE_ID = "emp_001"
SEED_PIN = "1234"

NON_CLAIMS = [
    "live verification used a temporary app copy only; the real runtime ledger is untouched",
    "no production deployment, hosting, or release seal claim",
    "no legal/payroll/cannabis compliance seal",
    "no payroll-provider integration",
]


# ---------------------------------------------------------------------------
# small HTTP helpers (stdlib only)
# ---------------------------------------------------------------------------
def _load_server(server_path: Path):
    """Dynamically load server.py from an arbitrary path (mirrors start_kiosk_server.py)."""
    spec = importlib.util.spec_from_file_location("bbtc_onboard_server", server_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _get_json(url: str, timeout: float):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _post_json(url: str, body: dict, timeout: float):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # /api/clock returns 403 for rejected punches
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except Exception:
            return exc.code, {"ok": False, "error": "non-json error body"}


# ---------------------------------------------------------------------------
# phases
# ---------------------------------------------------------------------------
def phase_environment_check() -> dict:
    notes: list[str] = []
    vi = sys.version_info
    py_ok = vi >= (3, 9)
    if not py_ok:
        notes.append(f"Python {vi.major}.{vi.minor} detected; this app needs 3.9+ (3.11+ recommended).")
    elif vi < (3, 11):
        notes.append(f"Python {vi.major}.{vi.minor} works; 3.11+ is recommended.")

    required = {
        "repo_scaffold/app/server.py": APP / "server.py",
        "repo_scaffold/app/config/settings.json": SETTINGS_PATH,
        "repo_scaffold/app/config/employees.seed.json": SEED_PATH,
        "scripts/start_kiosk_server.py": ROOT / "scripts" / "start_kiosk_server.py",
        "VERSION": ROOT / "VERSION",
    }
    missing = [rel for rel, path in required.items() if not path.exists()]
    if missing:
        notes.append("Missing expected paths: " + ", ".join(missing))

    status = "pass" if py_ok and not missing else "fail"
    return {
        "phase": "environment_check",
        "status": status,
        "python_version": f"{vi.major}.{vi.minor}.{vi.micro}",
        "missing_paths": missing,
        "notes": notes,
    }


def phase_config_check() -> dict:
    notes: list[str] = []
    warnings: list[str] = []
    surface: dict = {}
    try:
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "phase": "config_check",
            "status": "fail",
            "warnings": [],
            "notes": [f"Could not read settings.json: {exc}"],
            "surface": {},
        }

    if settings.get("owner_token") == DEFAULT_OWNER_TOKEN:
        warnings.append("owner_token is still the default (CHANGE_ME_OWNER_TOKEN) - change it before live use.")
    if settings.get("pin_pepper") == DEFAULT_PIN_PEPPER:
        warnings.append("pin_pepper is still the default (CHANGE_ME_PIN_PEPPER) - change it before live use.")

    surface = {
        "site_display_name": settings.get("site_display_name"),
        "timezone": settings.get("timezone"),
        "min_pin_length": settings.get("min_pin_length"),
        "allowed_export_formats": settings.get("allowed_export_formats"),
    }
    if not warnings:
        notes.append("Both secrets have been changed from their defaults.")

    # Default secrets are an advisory setup step, not a hard failure for onboarding.
    status = "warn" if warnings else "pass"
    return {
        "phase": "config_check",
        "status": status,
        "warnings": warnings,
        "notes": notes,
        "surface": surface,
    }


def phase_live_verification(requested_port: int, owner_token: str | None, timeout: float) -> dict:
    steps: list[dict] = []

    def step(name: str, ok: bool, detail) -> bool:
        steps.append({"step": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    tmp = Path(tempfile.mkdtemp(prefix="bbtc_onboard_"))
    httpd = None
    try:
        app_copy = tmp / "app"
        shutil.copytree(APP, app_copy, ignore=shutil.ignore_patterns("data", "__pycache__", "*.pyc"))
        mod = _load_server(app_copy / "server.py")
        mod.init_db()

        class QuietHandler(mod.Handler):  # silence per-request stderr logging
            def log_message(self, *args, **kwargs):
                return

        httpd = ThreadingHTTPServer(("127.0.0.1", requested_port), QuietHandler)
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{port}"

        # 1) health poll
        healthy = False
        deadline = time.time() + timeout
        health_body: dict = {}
        while time.time() < deadline:
            try:
                code, health_body = _get_json(base + "/api/health", 2.0)
                if code == 200 and health_body.get("ok"):
                    healthy = True
                    break
            except Exception:
                time.sleep(0.15)
        all_ok = step("health", healthy, {"version": health_body.get("version"), "site_id": health_body.get("site_id")})

        if healthy:
            # 2) clock lifecycle
            for ev in ("clock_in", "break_start", "break_end", "clock_out"):
                code, body = _post_json(
                    base + "/api/clock",
                    {"employee_id": SEED_EMPLOYEE_ID, "pin": SEED_PIN, "event_type": ev, "source": "onboarding_check"},
                    timeout,
                )
                ok = code == 200 and body.get("ok") is True
                detail = {"http": code, "validation_status": (body.get("event") or {}).get("validation_status")}
                if ev == "clock_out":
                    detail["receipt_message"] = (body.get("punch_receipt") or {}).get("message")
                all_ok = step(ev, ok, detail) and all_ok

            # 3) employee summary
            code, body = _post_json(
                base + "/api/employee/summary",
                {"employee_id": SEED_EMPLOYEE_ID, "pin": SEED_PIN},
                timeout,
            )
            sum_ok = code == 200 and body.get("ok") is True
            all_ok = step("employee_summary", sum_ok, {"http": code, "current_status": body.get("current_status")}) and all_ok

            # 4) bad pin must be rejected
            code, body = _post_json(
                base + "/api/clock",
                {"employee_id": SEED_EMPLOYEE_ID, "pin": "0000", "event_type": "clock_in", "source": "onboarding_check"},
                timeout,
            )
            bad_rejected = code == 403 and body.get("ok") is False
            all_ok = step("bad_pin_rejected", bad_rejected, {"http": code}) and all_ok

            # 5) optional owner summary (only when a token is explicitly provided)
            if owner_token:
                try:
                    code, body = _get_json(base + f"/api/owner/summary?owner_token={owner_token}", timeout)
                    owner_ok = code == 200
                    step("owner_summary", owner_ok, {"http": code})
                    all_ok = owner_ok and all_ok
                except Exception as exc:
                    step("owner_summary", False, {"error": str(exc)})
                    all_ok = False

        status = "pass" if all_ok else "fail"
        return {"phase": "live_verification", "status": status, "steps": steps}
    except Exception as exc:
        steps.append({"step": "setup", "ok": False, "detail": {"error": str(exc)}})
        return {"phase": "live_verification", "status": "fail", "steps": steps}
    finally:
        if httpd is not None:
            try:
                httpd.shutdown()
                httpd.server_close()
            except Exception:
                pass
        shutil.rmtree(tmp, ignore_errors=True)


def build_next_steps() -> list[str]:
    return [
        "Change owner_token and pin_pepper in repo_scaffold/app/config/settings.json.",
        "Start the kiosk server: python scripts/start_kiosk_server.py --host 0.0.0.0 --port 8080",
        "Owner console: open http://YOUR-COMPUTER-IP:8080/ on the owner device.",
        "Employee portal: open http://YOUR-COMPUTER-IP:8080/employee on phones/tablets.",
        "Employees clock in/out with their employee_id and PIN.",
    ]


# ---------------------------------------------------------------------------
# orchestration + output
# ---------------------------------------------------------------------------
def run(args) -> dict:
    phases = [phase_environment_check(), phase_config_check()]

    if args.no_live:
        phases.append({"phase": "live_verification", "status": "skipped", "steps": [], "notes": ["--no-live: live verification skipped"]})
    else:
        phases.append(phase_live_verification(args.port, args.owner_token, args.timeout))

    by_name = {p["phase"]: p for p in phases}
    env_ok = by_name["environment_check"]["status"] == "pass"
    cfg_ok = by_name["config_check"]["status"] in {"pass", "warn"}
    live_ok = by_name["live_verification"]["status"] in {"pass", "skipped"}
    overall = "pass" if env_ok and cfg_ok and live_ok else "fail"

    return {
        "program": "scripts/onboard_bbtc.py",
        "version": VERSION,
        "overall_status": overall,
        "phases": phases,
        "next_steps": build_next_steps(),
        "non_claims": NON_CLAIMS,
    }


def render_human(payload: dict) -> None:
    print("Best Buds Time Clock - Onboarding")
    print("=" * 58)
    print(f"Version: {payload['version']}")
    print(f"Overall: {payload['overall_status'].upper()}")

    for phase in payload["phases"]:
        print(f"\n[{phase['phase']}] -> {phase['status'].upper()}")
        for note in phase.get("notes", []):
            print(f"  - {note}")
        for warn in phase.get("warnings", []):
            print(f"  ! {warn}")
        surface = phase.get("surface")
        if surface:
            for key, value in surface.items():
                print(f"  {key}: {value}")
        for s in phase.get("steps", []):
            mark = "ok" if s["ok"] else "FAIL"
            print(f"  [{mark}] {s['step']}")

    print("\nNext steps:")
    for step in payload["next_steps"]:
        print(f"  - {step}")

    print("\nNon-claims:")
    for nc in payload["non_claims"]:
        print(f"  - {nc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Guided + live-verifying onboarding for the Best Buds Time Clock app")
    parser.add_argument("--agent", action="store_true", help="machine mode: emit canonical JSON (alias of --json)")
    parser.add_argument("--json", action="store_true", help="machine mode: emit canonical JSON")
    parser.add_argument("--no-live", action="store_true", help="skip the live verification phase (informational only)")
    parser.add_argument("--port", type=int, default=0, help="port for the ephemeral verification server (0 = pick a free port)")
    parser.add_argument("--owner-token", default=None, help="optional owner token to also verify an owner endpoint")
    parser.add_argument("--timeout", type=float, default=10.0, help="per-request / health-poll timeout in seconds")
    parser.add_argument("--yes", action="store_true", help="run live verification without the interactive prompt")
    args = parser.parse_args()

    machine = args.agent or args.json

    # In an interactive human session, offer to skip the (slower) live verification.
    if not machine and not args.no_live and not args.yes and sys.stdin.isatty():
        try:
            answer = input("Run live end-to-end verification now? [Y/n] ").strip().lower()
        except EOFError:
            answer = "y"
        if answer in {"n", "no"}:
            args.no_live = True

    payload = run(args)

    if machine:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        render_human(payload)

    return 0 if payload["overall_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read-only onboarding entrypoint for Cursor/developer agents.

This script prints the canonical repo state, source-of-truth paths, safe validators,
and non-claim boundaries. It does not start the app, make network calls, or modify files.
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    "README.md", "VERSION", "CHANGELOG.md", "repo_release_state.json", "package.json", "guide_pack.json",
    "contracts", "docs", "cursor", "pipeline", "scripts", "validation", "release_candidate", "reports", "context", "repo_scaffold", "manifests",
]
SAFE_COMMANDS = [
    "python scripts/validate_agent_onboarding_entrypoint.py",
    "python scripts/validate_product_user_entrypoint.py",
    "python scripts/validate_employee_qr_entry.py",
    "python scripts/validate_dev_startup_scripts.py",
    "python scripts/validate_repo.py",
    "python scripts/runtime_smoke.py  # temporary app-copy smoke only",
    "python scripts/start_kiosk_server.py --host 0.0.0.0 --port 8080  # operator-run local server, not a deployment claim",
]
NON_CLAIMS = [
    "no production deployment claim",
    "no release seal claim",
    "no QEMU/ISO/Boot Pod/systemd/rootfs claim",
    "no legal/payroll/cannabis compliance seal",
    "no payroll-provider integration",
    "offline browser queue is recovery evidence only",
    "CSV ledger is a mirror/export only",
]

def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": str(exc)}

def build_payload() -> dict:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "unknown"
    state = load_json(ROOT / "repo_release_state.json") if (ROOT / "repo_release_state.json").exists() else {}
    missing = [rel for rel in EXPECTED if not (ROOT / rel).exists()]
    return {
        "entrypoint": "scripts/onboard_agent.py",
        "mode": "read_only_agent_onboarding",
        "package_name": state.get("package_name", "best_buds_timeclock_capsule"),
        "version": version,
        "current_internal_phase": state.get("current_internal_phase", "unknown"),
        "next_internal_phase": state.get("next_internal_phase", "unknown"),
        "source_of_truth": [
            "VERSION", "repo_release_state.json", "README.md", "CHANGELOG.md", "package.json", "guide_pack.json",
            "release_candidate/", "validation/", "reports/", "context/resume_pack/", "frontend/save_state/",
        ],
        "safe_validation_commands": SAFE_COMMANDS,
        "non_claims": NON_CLAIMS,
        "warnings": [
            "Run from the repository root for path checks to align." if Path.cwd() != ROOT else "Running from repository root.",
            f"Missing expected paths: {', '.join(missing)}" if missing else "Required high-level paths found.",
            "This script is read-only and does not start the backend server.",
        ],
        "next_recommended_command": "continue rc7_7_owner_employee_admin_clarity",
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only agent onboarding for Best Buds Time Clock Capsule")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    payload = build_payload()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("Best Buds Time Clock Capsule — Agent Onboarding")
        print("=" * 58)
        print(f"Package: {payload['package_name']}")
        print(f"Version: {payload['version']}")
        print(f"Current phase: {payload['current_internal_phase']}")
        print(f"Next phase: {payload['next_internal_phase']}")
        print("\nRead first:")
        for item in payload["source_of_truth"]: print(f"- {item}")
        print("\nSafe validation commands:")
        for cmd in payload["safe_validation_commands"]: print(f"- {cmd}")
        print("\nNon-claims:")
        for nc in payload["non_claims"]: print(f"- {nc}")
        print("\nWarnings:")
        for w in payload["warnings"]: print(f"- {w}")
        print(f"\nNext: {payload['next_recommended_command']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

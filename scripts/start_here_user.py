#!/usr/bin/env python3
"""Product-facing start-here helper for owners/operators.

This is not a developer agent prompt. It prints the minimal steps needed to run and use
the time clock locally after the ZIP is unzipped.
"""
from __future__ import annotations
import argparse, json, socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def local_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ":" not in ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips

def payload():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "unknown"
    urls = [f"http://{ip}:8080" for ip in local_ips()] or ["http://YOUR-COMPUTER-IP:8080"]
    return {
        "entrypoint": "scripts/start_here_user.py",
        "mode": "product_operator_start_here",
        "version": version,
        "step_1_unzip": "Unzip the full repo package to a short path such as C:\\bbtc\\bbtc_v0_8_5.",
        "step_2_start_backend": "python scripts/start_kiosk_server.py --host 0.0.0.0 --port 8080",
        "step_3_phone_url_examples": urls,
        "employee_gold_path": ["Enter Employee ID", "Enter PIN", "Tap Clock In/Out", "Read receipt", "Confirm synced/owner-review status"],
        "owner_gold_path": ["Enter owner token", "Review Today", "Export", "Close Pay Period", "Backup", "Verify"],
        "offline_rule": "Offline punches are local recovery evidence until synced and reviewed by owner.",
        "non_claims": ["not a hosted deployment", "not a payroll provider", "not a legal/compliance seal", "not production-certified"],
    }

def main():
    parser = argparse.ArgumentParser(description="Product start-here helper for Best Buds Time Clock")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = payload()
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True)); return 0
    print("Best Buds Time Clock — Product Start Here")
    print("=" * 50)
    print(f"Version: {data['version']}")
    print("\n1) Unzip to a short Windows path:")
    print("   C:\\bbtc\\bbtc_v0_8_5")
    print("\n2) Start the local backend:")
    print(f"   {data['step_2_start_backend']}")
    print("\n3) Open on phone/tablet using one printed URL, for example:")
    for url in data['step_3_phone_url_examples']:
        print(f"   {url}")
    print("\nEmployee flow:")
    for step in data['employee_gold_path']: print(f"- {step}")
    print("\nOwner flow:")
    for step in data['owner_gold_path']: print(f"- {step}")
    print(f"\nOffline rule: {data['offline_rule']}")
    print("\nBoundaries:")
    for item in data['non_claims']: print(f"- {item}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

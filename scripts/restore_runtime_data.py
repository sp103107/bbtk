#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "repo_scaffold" / "app"

def load_server():
    spec = importlib.util.spec_from_file_location("bbtc_restore_server", APP / "server.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def main() -> int:
    ap = argparse.ArgumentParser(description="Verify a Best Buds runtime backup and optionally perform a dry-run restore into a candidate folder.")
    ap.add_argument("--backup", required=True, help="Path to backup ZIP")
    ap.add_argument("--target", default=None, help="Restore candidate target directory. Defaults under app/data/restore_candidates.")
    ap.add_argument("--apply", action="store_true", help="Deliberately replace app/data with backup content after verification. Not used by package validation.")
    args = ap.parse_args()
    mod = load_server()
    mod.init_db()
    backup = Path(args.backup).resolve()
    target = Path(args.target).resolve() if args.target else None
    receipt = mod.restore_dry_run(backup, target)
    if args.apply:
        if receipt.get("status") != "pass":
            print(json.dumps({"status":"fail","error":"dry_run_failed_apply_blocked","receipt":receipt}, indent=2, sort_keys=True))
            return 1
        if target is None:
            print(json.dumps({"status":"fail","error":"explicit_target_required_for_apply","receipt":receipt}, indent=2, sort_keys=True))
            return 1
        live_data = APP / "data"
        backup_existing = APP / f"data.pre_restore_backup_{mod.utc_now().strftime('%Y%m%dT%H%M%S')}"
        if live_data.exists():
            shutil.copytree(live_data, backup_existing)
        for item in target.iterdir():
            if item.name == "restore_dry_run_receipt.json":
                continue
            dest = live_data / item.name
            if dest.exists():
                if dest.is_dir(): shutil.rmtree(dest)
                else: dest.unlink()
            if item.is_dir(): shutil.copytree(item, dest)
            else: shutil.copy2(item, dest)
        receipt["apply_status"] = "applied"
        receipt["pre_restore_backup"] = str(backup_existing)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt.get("status") == "pass" else 1
if __name__ == "__main__":
    sys.exit(main())

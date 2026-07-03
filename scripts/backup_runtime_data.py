#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"repo_scaffold"/"app"

def load_server():
    spec=importlib.util.spec_from_file_location("bbtc_backup_server", APP/"server.py")
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def main()->int:
    ap=argparse.ArgumentParser(description="Create a manifest-backed runtime data backup.")
    ap.add_argument("--data-dir", default=str(APP/"data"), help="Retained for compatibility; app data dir is controlled by server module.")
    ap.add_argument("--output-dir", default=None, help="Optional external output directory copy.")
    args=ap.parse_args()
    mod=load_server(); mod.init_db()
    result=mod.create_runtime_backup()
    if args.output_dir:
        out=Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
        copied=out/Path(result["backup_file"]).name
        shutil.copy2(result["backup_file"], copied)
        result["external_copy"] = str(copied)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
if __name__=="__main__": sys.exit(main())

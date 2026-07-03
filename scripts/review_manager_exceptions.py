#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "repo_scaffold/app/server.py"

def load_server():
    spec = importlib.util.spec_from_file_location("bbtc_server_review", APP)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    mod = load_server()
    mod.init_db()
    if args.write:
        p = mod.write_owner_review_report(args.start, args.end)
        print(json.dumps({"status":"pass","review_file":str(p),"sha256":mod.path_hash(p)}, indent=2, sort_keys=True))
    else:
        print(json.dumps(mod.owner_review_report(args.start, args.end), indent=2, sort_keys=True))
    return 0
if __name__ == "__main__": sys.exit(main())

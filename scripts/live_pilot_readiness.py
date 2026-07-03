#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SERVER=ROOT/'repo_scaffold/app/server.py'
REPORT=ROOT/'reports/live_pilot_readiness_report.v0.8.0.json'

def load_server():
    spec=importlib.util.spec_from_file_location('bbtc_server_for_pilot_readiness', SERVER)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def main() -> int:
    mod=load_server()
    report=mod.pilot_readiness_report()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get('status') in {'ready','ready_with_warnings'} else 1
if __name__=='__main__': sys.exit(main())

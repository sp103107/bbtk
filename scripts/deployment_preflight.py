#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, socket, sys, datetime as dt, ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"repo_scaffold"/"app"
REPORT=ROOT/"reports"/"deployment_preflight_report.v0.8.0.json"

def load_server():
    spec=importlib.util.spec_from_file_location("bbtc_preflight_server", APP/"server.py")
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def port_available(host:str, port:int)->bool:
    s=socket.socket()
    try:
        s.bind((host, port)); return True
    except OSError:
        return False
    finally:
        s.close()

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    args=ap.parse_args()
    errors=[]; warnings=[]; checks={}
    try:
        ast.parse((APP/"server.py").read_text(encoding="utf-8")); checks["server_python_parses"]=True
    except Exception as e:
        checks["server_python_parses"]=False; errors.append(f"server_python_parse_failed:{e}")
    mod=load_server()
    try:
        mod.init_db(); checks["init_db"]=True
    except Exception as e:
        checks["init_db"]=False; errors.append(f"init_db_failed:{e}")
    for p in [mod.DATA_DIR, mod.LEDGER_DIR, mod.EXPORT_DIR, mod.BACKUP_DIR, mod.RESTORE_DIR, getattr(mod, "PILOT_DIR", mod.DATA_DIR/"pilot")]:
        try:
            p.mkdir(parents=True, exist_ok=True)
            test=p/".preflight_write_test"; test.write_text("ok", encoding="utf-8"); test.unlink()
            checks[f"writable:{p.relative_to(APP)}"]=True
        except Exception as e:
            checks[f"writable:{p.relative_to(APP)}"]=False; errors.append(f"not_writable:{p}:{e}")
    setup=mod.setup_warnings()
    checks["owner_token_changed"]="owner_token_default_change_required" not in setup
    checks["pin_pepper_changed"]="pin_pepper_default_change_required" not in setup
    if not checks["owner_token_changed"]: warnings.append("owner_token_default_change_required_before_live_use")
    if not checks["pin_pepper_changed"]: warnings.append("pin_pepper_default_change_required_before_live_use")
    checks["bind_host_loopback_default"] = args.host in {"127.0.0.1", "localhost"}
    if not checks["bind_host_loopback_default"]: warnings.append("non_loopback_bind_requires_network_policy_review")
    checks["port_available"] = port_available(args.host, args.port)
    if not checks["port_available"]: warnings.append(f"port_not_available_or_already_in_use:{args.host}:{args.port}")
    report={
        "version":"0.8.0",
        "checked_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "host":args.host,"port":args.port,
        "status":"fail" if errors else ("warn" if warnings else "pass"),
        "checks":checks,"errors":errors,"warnings":warnings,
        "non_claims":["preflight does not start a production server","preflight does not prove legal compliance","preflight warnings must be resolved before live use"]
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if errors else 0
if __name__=="__main__": sys.exit(main())

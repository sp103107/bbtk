#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, sys
from pathlib import Path

def sha_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

def event_hash(event: dict) -> str:
    e = dict(event)
    e.pop("event_hash", None)
    return sha_text(json.dumps(e, sort_keys=True, separators=(",", ":")))

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="repo_scaffold/app/data")
    ap.add_argument("--output", default=None)
    args = ap.parse_args()
    data_dir = Path(args.data_dir)
    ledger_dir = data_dir / "ledger" / "clock_events"
    errors=[]; count=0; prev="sha256:GENESIS"; h=hashlib.sha256()
    for p in sorted(ledger_dir.glob("**/*.jsonl")):
        raw=p.read_bytes(); h.update(raw)
        for i,line in enumerate(raw.decode("utf-8").splitlines(),1):
            if not line.strip(): continue
            count+=1
            try: event=json.loads(line)
            except Exception as e:
                errors.append(f"json_parse_failed:{p}:{i}:{e}"); continue
            if event.get("prev_event_hash") != prev:
                errors.append(f"prev_hash_mismatch:{p}:{i}")
            expected=event_hash(event)
            if event.get("event_hash") != expected:
                errors.append(f"event_hash_mismatch:{p}:{i}")
            prev=event.get("event_hash", "sha256:UNKNOWN")
    report={"checked_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"status":"pass" if not errors else "fail","event_count":count,"ledger_hash":"sha256:"+h.hexdigest(),"errors":errors}
    text=json.dumps(report,indent=2,sort_keys=True)+"\n"
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True); Path(args.output).write_text(text, encoding="utf-8")
    print(text)
    return 0 if not errors else 1
if __name__=="__main__": sys.exit(main())

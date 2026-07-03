#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, sys, zipfile
from pathlib import Path

def sha(path: Path) -> str:
    h=hashlib.sha256(); h.update(path.read_bytes()); return "sha256:"+h.hexdigest()

def main() -> int:
    ap=argparse.ArgumentParser(description="Verify a closed Best Buds pay-period package folder.")
    ap.add_argument("period_dir", nargs="?", default="repo_scaffold/app/data/pay_periods", help="Period folder or pay_periods root")
    args=ap.parse_args()
    root=Path(args.period_dir)
    manifests=[root/"pay_period_manifest.json"] if (root/"pay_period_manifest.json").exists() else list(root.glob("**/pay_period_manifest.json"))
    errors=[]; checked=[]
    for manifest in manifests:
        data=json.loads(manifest.read_text(encoding="utf-8"))
        period_dir=manifest.parent
        for rel, expected in data.get("file_hashes", {}).items():
            p=period_dir/rel
            if not p.exists(): errors.append(f"missing_file:{p}"); continue
            actual=sha(p)
            if actual != expected: errors.append(f"hash_mismatch:{p}:{actual}!={expected}")
        archive=period_dir/f"{data.get('period_id')}.zip"
        if archive.exists() and not zipfile.is_zipfile(archive): errors.append(f"invalid_zip:{archive}")
        checked.append(str(manifest))
    report={"status":"pass" if not errors else "fail","checked_manifests":checked,"errors":errors}
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0 if not errors else 1
if __name__=="__main__": sys.exit(main())

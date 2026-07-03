#!/usr/bin/env python3
"""Build the v0.8.6 full-repo release-candidate ZIP (bbtc_v0_8_6.zip).

Packages the repository under a short root folder name for Windows path-length safety.
Excludes local-only artifacts, caches, and nested ZIP files.
"""
from __future__ import annotations

import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
STATE = json.loads((ROOT / "repo_release_state.json").read_text(encoding="utf-8"))
ZIP_NAME = STATE.get("zip_name_policy", {}).get("short_zip_name", f"bbtc_v0_8_6.zip")
ROOT_NAME = STATE.get("zip_name_policy", {}).get("short_repo_root", "bbtc_v0_8_6")
PHASE = STATE.get("current_internal_phase", "rc7_6_employee_qr_entry_and_kiosk_fit")

EXCLUDE_DIR_NAMES = {".git", "__pycache__", ".cursor", "node_modules"}
EXCLUDE_FILE_NAMES = {ZIP_NAME}
EXCLUDE_SUFFIXES = {".pyc", ".zip"}
EXCLUDE_REL_PATHS = {
    "development/local_library_bindings.json",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def should_include(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if rel in EXCLUDE_REL_PATHS:
        return False
    if path.name in EXCLUDE_FILE_NAMES:
        return False
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return False
    for part in path.parts:
        if part in EXCLUDE_DIR_NAMES:
            return False
    return True


def default_output_path() -> Path:
    parent = ROOT.parent
    return parent / ZIP_NAME


def build_zip(out_path: Path) -> dict:
    files: list[dict] = []
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file() or not should_include(path):
                continue
            rel = path.relative_to(ROOT).as_posix()
            arcname = f"{ROOT_NAME}/{rel}"
            zf.write(path, arcname)
            files.append({"path": rel, "size_bytes": path.stat().st_size})
    zip_hash = sha256_file(out_path)
    return {
        "version": VERSION,
        "phase": PHASE,
        "zip_name": out_path.name,
        "zip_path": str(out_path.resolve()),
        "zip_root_folder": ROOT_NAME,
        "file_count": len(files),
        "zip_bytes": out_path.stat().st_size,
        "sha256": zip_hash,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "non_claims": [
            "Release-candidate ZIP packaging only.",
            "No production deployment claim.",
            "No release seal claim.",
        ],
        "runtime_claimed": False,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Package Best Buds Time Clock Capsule release-candidate ZIP")
    parser.add_argument("--output", type=Path, default=default_output_path(), help="Output ZIP path")
    args = parser.parse_args()
    receipt = build_zip(args.output.resolve())
    rc_dir = ROOT / "release_candidate" / "rc7_6_employee_qr_entry_and_kiosk_fit"
    rc_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = rc_dir / f"package_zip_receipt.v{VERSION}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = json.loads((ROOT / "reports" / f"release_manifest.v{VERSION}.json").read_text(encoding="utf-8"))
    manifest["zip_status"] = "packaged"
    manifest["zip_path"] = receipt["zip_path"]
    manifest["zip_sha256"] = receipt["sha256"]
    manifest["zip_file_count"] = receipt["file_count"]
    manifest["generated_at"] = receipt["generated_at"]
    (ROOT / "reports" / f"release_manifest.v{VERSION}.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

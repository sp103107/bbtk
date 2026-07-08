#!/usr/bin/env python3
"""Audit company branding references before creating branded time-clock clones.

The report separates runtime branding that should become company-configurable from
historical/internal references that should usually remain untouched.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_SCAN_PATHS = [
    "repo_scaffold/app",
    "scripts",
    "docs",
    "contracts",
    "README.md",
    "package.json",
    "guide_pack.json",
]

EXCLUDED_PARTS = {
    ".git",
    "__pycache__",
    "node_modules",
    "data",
    "backups",
    "restore_candidates",
    "exports",
    "output",
    "outputs",
    "tmp",
}

TEXT_EXTENSIONS = {
    ".bat",
    ".css",
    ".csv",
    ".html",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".mjs",
    ".py",
    ".schema",
    ".sh",
    ".svg",
    ".txt",
    ".xml",
    ".yml",
    ".yaml",
}

PATTERNS = [
    ("best_buds_full", re.compile(r"Best Buds Cannabis Cultivation(?:\s*[—-]\s*West Warwick,\s*RI)?", re.I)),
    ("best_buds", re.compile(r"Best Buds", re.I)),
    ("bbtc_upper", re.compile(r"\bBBTC\b")),
    ("bbtc_lower", re.compile(r"\bbbtc\b")),
    ("hemp_logo", re.compile(r"hemp-bud-mark\.svg", re.I)),
    ("site_display_name", re.compile(r"site_display_name")),
    ("site_id", re.compile(r"site_id")),
    ("owner_console_title", re.compile(r"Owner Console")),
    ("time_clock_title", re.compile(r"Time Clock")),
]


@dataclass
class BrandingHit:
    path: str
    line: int
    pattern: str
    match: str
    category: str
    replacement_key: str | None
    safe_to_template: bool
    text: str


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"README", "VERSION"}


def classify(path: Path, pattern_name: str, line_text: str) -> tuple[str, str | None, bool]:
    normalized = str(path).replace("\\", "/")
    runtime = normalized.startswith("repo_scaffold/app/")
    static = normalized.startswith("repo_scaffold/app/static/")
    config = normalized.startswith("repo_scaffold/app/config/")
    historical = normalized.startswith(("docs/", "contracts/", "context/", "manifests/", "validation/", "reports/"))

    if pattern_name == "hemp_logo":
        return ("asset_branding" if runtime else "historical_docs", "branding.logo_path", runtime)
    if pattern_name in {"site_display_name", "site_id"}:
        return ("data_branding" if runtime or config else "historical_docs", f"company.{pattern_name}", runtime or config)
    if pattern_name in {"bbtc_lower", "bbtc_upper"}:
        if any(token in line_text for token in ["bbtc_owner_", "bbtc_backup_", "bbtc_admin_session_", "bbtc_offline_"]):
            return ("internal_namespace", None, False)
        if "zip" in line_text.lower() or "folder" in line_text.lower() or "path" in line_text.lower():
            return ("package_branding", "package.folder_name", False)
        return ("internal_namespace", None, False)
    if runtime and static:
        return ("runtime_branding", "company.display_name", True)
    if runtime:
        return ("runtime_branding", "company.display_name", True)
    if historical:
        return ("historical_docs", None, False)
    if normalized in {"README.md", "package.json", "guide_pack.json"} or normalized.startswith("scripts/"):
        return ("package_branding", "package.display_name", False)
    return ("review_required", None, False)


def iter_files(root: Path, scan_paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for item in scan_paths:
        target = root / item
        if not target.exists():
            continue
        if target.is_file():
            if is_text_file(target) and not is_excluded(target):
                files.append(target)
            continue
        for path in target.rglob("*"):
            if path.is_file() and is_text_file(path) and not is_excluded(path):
                files.append(path)
    return sorted(set(files))


def audit(root: Path, scan_paths: list[str]) -> list[BrandingHit]:
    hits: list[BrandingHit] = []
    for path in iter_files(root, scan_paths):
        rel = path.relative_to(root)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, text in enumerate(lines, start=1):
            for pattern_name, pattern in PATTERNS:
                for match in pattern.finditer(text):
                    category, replacement_key, safe = classify(rel, pattern_name, text)
                    hits.append(
                        BrandingHit(
                            path=str(rel).replace("\\", "/"),
                            line=line_number,
                            pattern=pattern_name,
                            match=match.group(0),
                            category=category,
                            replacement_key=replacement_key,
                            safe_to_template=safe,
                            text=text.strip()[:240],
                        )
                    )
    return hits


def write_reports(root: Path, hits: list[BrandingHit], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "branding_reference_report.json"
    md_path = out_dir / "branding_reference_report.md"
    payload = {
        "status": "pass",
        "hit_count": len(hits),
        "category_counts": {},
        "safe_to_template_count": sum(1 for hit in hits if hit.safe_to_template),
        "hits": [asdict(hit) for hit in hits],
    }
    for hit in hits:
        payload["category_counts"][hit.category] = payload["category_counts"].get(hit.category, 0) + 1
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Branding Reference Report",
        "",
        f"- Total hits: {payload['hit_count']}",
        f"- Safe runtime template hits: {payload['safe_to_template_count']}",
        "",
        "## Category counts",
        "",
    ]
    for category, count in sorted(payload["category_counts"].items()):
        lines.append(f"- `{category}`: {count}")
    lines.extend(["", "## Hits", ""])
    for hit in hits:
        safe = "yes" if hit.safe_to_template else "no"
        key = hit.replacement_key or "n/a"
        lines.append(f"- `{hit.path}:{hit.line}` `{hit.category}` safe={safe} key=`{key}` match=`{hit.match}`")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Find Best Buds/BBTC/company branding references.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--out-dir", default="output/branding", help="Report output directory.")
    parser.add_argument("--scan-path", action="append", dest="scan_paths", help="Additional or replacement scan path. Can be repeated.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    scan_paths = args.scan_paths or DEFAULT_SCAN_PATHS
    hits = audit(root, scan_paths)
    json_path, md_path = write_reports(root, hits, root / args.out_dir)
    summary = {
        "status": "pass",
        "hit_count": len(hits),
        "json_report": str(json_path),
        "markdown_report": str(md_path),
    }
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"Branding audit complete: {len(hits)} hit(s)")
        print(f"JSON: {json_path}")
        print(f"Markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

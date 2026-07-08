#!/usr/bin/env python3
"""Validate that runtime/package artifacts are portable across devices.

This check is intentionally focused on operational files, not historical reports.
It rejects user-specific Windows home paths, version-pinned local workspace paths,
and generated absolute output paths inside company clone ZIPs.
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TEXT_EXTENSIONS = {
    ".bat",
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".svg",
    ".txt",
    ".yml",
    ".yaml",
}

DEFAULT_SCOPE = [
    ".gitignore",
    "README.md",
    "VERSION",
    "contracts/company_branding_profile.example.json",
    "docs/COMPANY_BRANDING_CLONE_PORTER.md",
    "repo_scaffold/app",
    "scripts",
]

EXCLUDED_PARTS = {
    "__pycache__",
    "data",
    "output",
    "outputs",
    "reports",
    "validation",
}

DISALLOWED_PATTERNS = [
    ("user_home_path", re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"']+", re.I)),
    ("version_pinned_workspace", re.compile(r"[A-Za-z]:[\\/]+bbtc_v\d+_\d+_\d+", re.I)),
    ("local_temp_path", re.compile(r"[A-Za-z]:[\\/]+(?:Windows[\\/]+Temp|Temp)[\\/]+", re.I)),
    ("file_uri_absolute", re.compile(r"file:///[A-Za-z]:/", re.I)),
]

ALLOWED_TEXT_SNIPPETS = {
    "C:\\\\bbtc",  # generic short-path guidance, not this device or version pinned
    "C:\\bbtc",
    "127.0.0.1",  # loopback default is portable and intentionally local
    "localhost",
}


@dataclass
class Finding:
    path: str
    line: int
    kind: str
    match: str
    text: str


def is_text_name(name: str) -> bool:
    return Path(name).suffix.lower() in TEXT_EXTENSIONS or Path(name).name in {"README", "VERSION"}


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def iter_repo_files(scope: list[str]) -> list[Path]:
    files: list[Path] = []
    for item in scope:
        target = ROOT / item
        if not target.exists():
            continue
        if target.is_file():
            if is_text_name(target.name) and not is_excluded(target.relative_to(ROOT)):
                files.append(target)
            continue
        for path in target.rglob("*"):
            if path.is_file() and is_text_name(path.name) and not is_excluded(path.relative_to(ROOT)):
                files.append(path)
    return sorted(set(files))


def scan_text(name: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if any(snippet in line for snippet in ALLOWED_TEXT_SNIPPETS):
            allowed_line = line.replace("C:\\bbtc", "").replace("C:\\\\bbtc", "")
        else:
            allowed_line = line
        for kind, pattern in DISALLOWED_PATTERNS:
            for match in pattern.finditer(allowed_line):
                findings.append(
                    Finding(
                        path=name,
                        line=line_number,
                        kind=kind,
                        match=match.group(0),
                        text=line.strip()[:240],
                    )
                )
    return findings


def scan_repo(scope: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_repo_files(scope):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text(str(path.relative_to(ROOT)).replace("\\", "/"), text))
    return findings


def scan_zip(zip_path: Path) -> list[Finding]:
    findings: list[Finding] = []
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if name.endswith("/") or not is_text_name(name):
                continue
            text = archive.read(name).decode("utf-8", errors="ignore")
            findings.extend(scan_text(name, text))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate runtime/package portability.")
    parser.add_argument("--zip", dest="zip_path", help="Optional company ZIP to scan.")
    parser.add_argument("--scope", action="append", help="Repo path scope. Can be repeated.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable report.")
    args = parser.parse_args()

    findings = scan_zip(Path(args.zip_path).resolve()) if args.zip_path else scan_repo(args.scope or DEFAULT_SCOPE)
    report = {
        "status": "pass" if not findings else "fail",
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
        "non_claims": [
            "Loopback URLs such as 127.0.0.1 are portable local defaults and are allowed.",
            "This check focuses on operational runtime/package files, not archived historical reports.",
        ],
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())

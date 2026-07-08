#!/usr/bin/env python3
"""Build a clean branded company ZIP from this time-clock app.

This packager intentionally does not copy runtime data, exports, backups, existing
owner tokens, backup tokens, or admin users into the cloned application.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "0.9.0"

EXCLUDE_DIR_NAMES = {
    ".git",
    "__pycache__",
    "context",
    "data",
    "frontend",
    "manifests",
    "release_candidate",
    "reports",
    "backups",
    "restore_candidates",
    "exports",
    "output",
    "outputs",
    "tmp",
    "_arc_blueprints_tmp",
    "validation",
}

EXCLUDE_FILE_NAMES = {
    "settings.json",
}

ALLOWED_TOP_LEVEL = {
    ".gitignore",
    "CHANGELOG.md",
    "README.md",
    "VERSION",
    "contracts",
    "docs",
    "package.json",
    "repo_scaffold",
    "requirements.txt",
    "scripts",
}

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
}


def slugify(value: str, fallback: str = "company_time_clock") -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    return slug or fallback


def load_profile(path: Path) -> dict:
    profile = json.loads(path.read_text(encoding="utf-8"))
    company = profile.get("company") or {}
    branding = profile.get("branding") or {}
    package = profile.get("package") or {}
    required = {
        "company.display_name": company.get("display_name"),
        "company.site_id": company.get("site_id"),
        "company.timezone": company.get("timezone"),
    }
    missing = [key for key, value in required.items() if not str(value or "").strip()]
    if missing:
        raise ValueError("missing_required_profile_fields: " + ", ".join(missing))
    profile.setdefault("branding", branding)
    profile.setdefault("package", package)
    profile.setdefault("security", {})
    package.setdefault("folder_name", slugify(company["display_name"]))
    package.setdefault("zip_name", f"{slugify(package['folder_name'])}.zip")
    branding.setdefault("app_short_name", f"{company['display_name']} Time Clock")
    branding.setdefault("primary_color", "#0f172a")
    branding.setdefault("accent_color", "#3730a3")
    return profile


def should_ignore(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if len(rel.parts) == 1 and rel.parts[0] not in ALLOWED_TOP_LEVEL:
        return True
    if rel.parts and rel.parts[0] not in ALLOWED_TOP_LEVEL:
        return True
    if any(part in EXCLUDE_DIR_NAMES for part in rel.parts):
        return True
    if path.name in EXCLUDE_FILE_NAMES and "repo_scaffold" in rel.parts and "config" in rel.parts:
        return True
    if path.suffix.lower() in {".pyc", ".sqlite3", ".zip", ".xlsx", ".csv"}:
        return True
    return False


def copy_clean_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if should_ignore(item, src):
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, ignore=lambda folder, names: [
                name for name in names if should_ignore(Path(folder) / name, src)
            ])
        else:
            shutil.copy2(item, target)


def neutral_logo_svg(company_name: str, primary: str, accent: str) -> str:
    initials = "".join(word[0] for word in re.findall(r"[A-Za-z0-9]+", company_name)[:2]).upper() or "TC"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="{company_name} logo">
  <rect width="128" height="128" rx="30" fill="{primary}"/>
  <circle cx="64" cy="64" r="42" fill="{accent}" opacity=".95"/>
  <text x="64" y="75" text-anchor="middle" font-family="Arial, sans-serif" font-size="34" font-weight="800" fill="#ffffff">{initials}</text>
</svg>
"""


def text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
            files.append(path)
    return files


def replace_text(path: Path, replacements: list[tuple[str, str]]) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return 0
    original = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return 1
    return 0


def sanitized_settings(profile: dict) -> dict:
    company = profile["company"]
    branding = profile["branding"]
    security = profile.get("security") or {}
    return {
        "allow_owner_adjustments": True,
        "allowed_export_formats": ["xlsx", "csv", "json", "markdown", "html"],
        "admin_auth_version": "1",
        "admin_users": [],
        "app_security_policy_version": "0.9.0",
        "branding": {
            "app_short_name": branding.get("app_short_name"),
            "primary_color": branding.get("primary_color"),
            "accent_color": branding.get("accent_color"),
            "logo_asset": "/static/company-logo.svg",
        },
        "clock_events": ["break_end", "break_start", "clock_in", "clock_out"],
        "clone_build": {
            "built_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source_version": APP_VERSION,
            "runtime_data_included": False,
            "owner_tokens_included": False,
            "admin_users_included": False,
        },
        "deployment_policy": {
            "bind_default": "127.0.0.1",
            "owner_token_must_change_from_default": True,
            "pin_pepper_must_change_from_default": True,
            "preflight_required_before_live_use": True,
        },
        "first_run": {
            "admin_setup_required": True,
            "suggested_admin_username": security.get("first_admin_username", "admin"),
        },
        "manager_review_required_before_pay_period_close": False,
        "min_pin_length": int(security.get("min_pin_length", 4) or 4),
        "owner_adjustment_reason_required": True,
        "owner_token": "CHANGE_ME_OWNER_TOKEN",
        "pin_pepper": "CHANGE_ME_PIN_PEPPER",
        "regular_hours_cap_per_week": 40,
        "runtime_version": APP_VERSION,
        "setup_required_when_default_secret": True,
        "site_display_name": company.get("legal_name") or company["display_name"],
        "site_id": company["site_id"],
        "terminal_id": company.get("terminal_id", "front_kiosk_01"),
        "timezone": company["timezone"],
    }


def apply_branding(staged_root: Path, profile: dict, profile_path: Path) -> dict:
    company = profile["company"]
    branding = profile["branding"]
    package = profile["package"]
    display_name = company["display_name"]
    app_short_name = branding["app_short_name"]
    app_label = branding.get("app_label", "Time Clock")
    operator_title = branding.get("operator_title", "Operator Console")
    primary = branding["primary_color"]
    accent = branding["accent_color"]
    replacements = [
        ("Best Buds Cannabis Cultivation â€” West Warwick, RI", company.get("legal_name") or display_name),
        ("Best Buds Cannabis Cultivation — West Warwick, RI", company.get("legal_name") or display_name),
        ("Best Buds · Owner Operations", f"{display_name} · Operations"),
        ("Best Buds Owner Console", f"{display_name} {operator_title}"),
        ("Best Buds Time Clock Kiosk", f"{display_name} {app_label} Kiosk"),
        ("Best Buds Time Clock Poster", f"{display_name} {app_label} Poster"),
        ("Best Buds Time Clock", app_short_name),
        ("Best Buds", display_name),
        ("Owner Console", operator_title),
        ("Shared Time Clock", app_label),
        ("Time Clock", app_label),
        ("hemp-bud-mark.svg", "company-logo.svg"),
        ("best_buds_west_warwick_ri", company["site_id"]),
        ("#0f172a", primary),
        ("#3730a3", accent),
        ("#4338ca", accent),
    ]
    changed_files = 0
    for path in text_files(staged_root):
        changed_files += replace_text(path, replacements)

    static_dir = staged_root / "repo_scaffold" / "app" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    logo_source = branding.get("logo_path")
    logo_target = static_dir / "company-logo.svg"
    if logo_source:
        source_path = (profile_path.parent / logo_source).resolve() if not Path(logo_source).is_absolute() else Path(logo_source)
        if not source_path.exists():
            raise FileNotFoundError(f"logo_path_not_found: {source_path}")
        shutil.copy2(source_path, logo_target)
    else:
        logo_target.write_text(neutral_logo_svg(display_name, primary, accent), encoding="utf-8")

    config_dir = staged_root / "repo_scaffold" / "app" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "settings.json").write_text(json.dumps(sanitized_settings(profile), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for data_dir in [
        staged_root / "repo_scaffold" / "app" / "data",
        staged_root / "output",
        staged_root / "outputs",
        staged_root / "tmp",
    ]:
        if data_dir.exists():
            shutil.rmtree(data_dir)
    (staged_root / "repo_scaffold" / "app" / "data").mkdir(parents=True, exist_ok=True)
    return {
        "changed_text_files": changed_files,
        "logo_asset": str(logo_target.relative_to(staged_root)).replace("\\", "/"),
        "settings_file": "repo_scaffold/app/config/settings.json",
    }


def make_zip(source_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir.parent).as_posix())


def build(profile_path: Path, out_dir: Path) -> dict:
    profile = load_profile(profile_path)
    folder_name = slugify(profile["package"]["folder_name"])
    zip_name = profile["package"]["zip_name"]
    if not zip_name.lower().endswith(".zip"):
        zip_name += ".zip"
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bbtc_company_clone_") as temp:
        staging_parent = Path(temp)
        staged_root = staging_parent / folder_name
        copy_clean_tree(ROOT, staged_root)
        branding_result = apply_branding(staged_root, profile, profile_path)
        zip_path = out_dir / zip_name
        make_zip(staged_root, zip_path)
    manifest = {
        "ok": True,
        "clone_id": f"company_clone_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "built_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_root": str(ROOT),
        "source_version": APP_VERSION,
        "profile": str(profile_path),
        "company": profile["company"],
        "package": {
            "folder_name": folder_name,
            "zip_name": zip_name,
            "zip_path": str(zip_path),
        },
        "branding": branding_result,
        "privacy": {
            "runtime_data_included": False,
            "exports_included": False,
            "backups_included": False,
            "owner_tokens_included": False,
            "admin_users_included": False,
        },
        "next_steps": [
            "Unzip the company ZIP to a short local path.",
            "Start the server on the company machine.",
            "Create the first administrator from the operator panel.",
            "Generate owner/recovery tokens from the Security tab.",
        ],
    }
    manifest_path = out_dir / f"{Path(zip_name).stem}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a clean branded company time-clock ZIP.")
    parser.add_argument("--profile", required=True, help="Company branding profile JSON.")
    parser.add_argument("--out-dir", default="output/company_zips", help="Output directory for ZIP and manifest.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable manifest.")
    args = parser.parse_args()
    manifest = build(Path(args.profile).resolve(), (ROOT / args.out_dir).resolve())
    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(f"Company clone ZIP created: {manifest['package']['zip_path']}")
        print(f"Manifest: {manifest['manifest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

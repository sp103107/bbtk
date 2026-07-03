#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "repo_scaffold" / "app"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
REPORT = ROOT / "validation" / f"owner_token_generator_validation_report.v{VERSION}.json"


def load_server(path: Path):
    spec = importlib.util.spec_from_file_location("bbtc_owner_token_validation_server", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def request_json(url: str, payload: dict | None = None) -> tuple[int, dict]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"} if body is not None else {},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def main() -> int:
    checks: dict[str, bool] = {}
    errors: list[str] = []
    server = None
    thread = None
    try:
        with tempfile.TemporaryDirectory(prefix="bbtc_owner_token_") as temp_dir:
            temp_app = Path(temp_dir) / "app"
            shutil.copytree(APP, temp_app)
            temp_settings_path = temp_app / "config" / "settings.json"
            temp_settings = json.loads(temp_settings_path.read_text(encoding="utf-8"))
            temp_settings["owner_token"] = "CHANGE_ME_OWNER_TOKEN"
            temp_settings.pop("owner_token_setup_method", None)
            temp_settings.pop("owner_token_updated_at_utc", None)
            temp_settings.pop("owner_backup_token_set", None)
            temp_settings_path.write_text(
                json.dumps(temp_settings, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            shutil.rmtree(temp_app / "data", ignore_errors=True)
            module = load_server(temp_app / "server.py")
            module.init_db()
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
            server = httpd
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{httpd.server_address[1]}"

            status_code, initial_status = request_json(base + "/api/security/owner-token/status")
            checks["initial_status_is_local_setup"] = (
                status_code == 200
                and initial_status.get("setup_required") is True
                and initial_status.get("local_request") is True
                and "owner_token" not in initial_status
            )

            create_code, created = request_json(base + "/api/security/owner-token/generate", {})
            first_token = str(created.get("owner_token", ""))
            initial_backup_tokens = created.get("backup_tokens") or []
            checks["initial_generation_succeeds"] = (
                create_code == 200
                and created.get("first_time_setup") is True
                and created.get("shown_once") is True
                and created.get("recovery_file_ready") is True
            )
            checks["initial_generation_includes_recovery_set"] = (
                len(initial_backup_tokens) == 10
                and len(set(initial_backup_tokens)) == 10
                and all(str(token).startswith("bbtc_backup_") for token in initial_backup_tokens)
            )
            checks["generated_token_is_strong"] = (
                first_token.startswith("bbtc_owner_")
                and len(first_token) >= 50
                and first_token != module.DEFAULT_OWNER_TOKEN
            )
            checks["token_persisted"] = module.settings().get("owner_token") == first_token
            initial_stored_set = module.load_json(module.SETTINGS_PATH, {}).get("owner_backup_token_set") or {}
            initial_stored_text = json.dumps(initial_stored_set)
            checks["initial_recovery_set_stored_as_hashes_only"] = (
                len(initial_stored_set.get("tokens") or []) == 10
                and all("token_hash" in record for record in initial_stored_set.get("tokens") or [])
                and all(str(token) not in initial_stored_text for token in initial_backup_tokens)
            )
            checks["default_warning_cleared"] = "owner_token_default_change_required" not in module.setup_warnings()
            local_addresses = module.local_computer_addresses()
            checks["local_computer_address_gate"] = (
                bool(local_addresses)
                and all(module.is_local_computer_address(address) for address in local_addresses)
                and not module.is_local_computer_address("203.0.113.123")
            )

            status_code, configured_status = request_json(base + "/api/security/owner-token/status")
            checks["configured_status_does_not_disclose_token"] = (
                status_code == 200
                and configured_status.get("configured") is True
                and "owner_token" not in configured_status
                and first_token not in json.dumps(configured_status)
            )

            bad_code, bad_rotation = request_json(
                base + "/api/security/owner-token/generate",
                {"owner_token": "definitely-not-the-current-token"},
            )
            checks["bad_rotation_rejected"] = (
                bad_code == 403
                and bad_rotation.get("error") == "owner_token_current_required_or_invalid"
                and module.verify_owner_token(first_token)
            )

            rotate_code, rotated = request_json(
                base + "/api/security/owner-token/generate",
                {"owner_token": first_token},
            )
            second_token = str(rotated.get("owner_token", ""))
            checks["authenticated_rotation_succeeds"] = (
                rotate_code == 200
                and rotated.get("first_time_setup") is False
                and "backup_tokens" not in rotated
                and second_token.startswith("bbtc_owner_")
                and second_token != first_token
                and module.load_json(module.SETTINGS_PATH, {}).get("owner_backup_token_set", {}).get("set_id")
                == initial_stored_set.get("set_id")
            )
            checks["old_token_revoked_new_token_valid"] = (
                not module.verify_owner_token(first_token)
                and module.verify_owner_token(second_token)
            )

            backup_code, backup_set_one = request_json(
                base + "/api/security/backup-tokens/generate",
                {"owner_token": second_token},
            )
            backup_tokens_one = backup_set_one.get("backup_tokens") or []
            checks["ten_unique_backup_tokens_generated"] = (
                backup_code == 200
                and len(backup_tokens_one) == 10
                and len(set(backup_tokens_one)) == 10
                and all(str(token).startswith("bbtc_backup_") and len(str(token)) >= 40 for token in backup_tokens_one)
            )
            stored_set_one = module.load_json(module.SETTINGS_PATH, {}).get("owner_backup_token_set") or {}
            stored_text_one = json.dumps(stored_set_one)
            checks["backup_tokens_stored_as_hashes_only"] = (
                len(stored_set_one.get("tokens") or []) == 10
                and all("token_hash" in record for record in stored_set_one.get("tokens") or [])
                and all(str(token) not in stored_text_one for token in backup_tokens_one)
            )

            replacement_code, backup_set_two = request_json(
                base + "/api/security/backup-tokens/generate",
                {"owner_token": second_token},
            )
            backup_tokens_two = backup_set_two.get("backup_tokens") or []
            old_backup_code, _ = request_json(
                base + "/api/security/backup-tokens/recover",
                {"backup_token": backup_tokens_one[0]},
            )
            checks["new_backup_set_invalidates_prior_set"] = (
                replacement_code == 200
                and len(backup_tokens_two) == 10
                and backup_set_two.get("backup_set_id") != backup_set_one.get("backup_set_id")
                and old_backup_code == 403
            )

            recovery_code, recovery = request_json(
                base + "/api/security/backup-tokens/recover",
                {"backup_token": backup_tokens_two[0]},
            )
            recovered_owner_token = str(recovery.get("owner_token", ""))
            reuse_code, reuse = request_json(
                base + "/api/security/backup-tokens/recover",
                {"backup_token": backup_tokens_two[0]},
            )
            checks["backup_token_recovers_and_is_single_use"] = (
                recovery_code == 200
                and recovery.get("backup_token_consumed") is True
                and recovery.get("backup_tokens_remaining") == 9
                and recovered_owner_token.startswith("bbtc_owner_")
                and not module.verify_owner_token(second_token)
                and module.verify_owner_token(recovered_owner_token)
                and reuse_code == 403
                and reuse.get("error") == "backup_token_invalid_or_used"
            )
            checks["atomic_temp_files_cleaned"] = not list(module.CONFIG_DIR.glob(".settings.*.tmp"))

            receipts = module.db_rows(
                "SELECT payload_json FROM audit_receipts WHERE receipt_type IN (?,?,?,?,?)",
                (
                    "owner_token_initialized",
                    "owner_token_rotated",
                    "owner_backup_token_set_initialized",
                    "owner_backup_token_set_replaced",
                    "owner_token_recovered",
                ),
            )
            receipt_text = json.dumps(receipts)
            checks["audit_receipts_redact_tokens"] = (
                len(receipts) == 6
                and first_token not in receipt_text
                and second_token not in receipt_text
                and recovered_owner_token not in receipt_text
                and all(str(token) not in receipt_text for token in initial_backup_tokens + backup_tokens_one + backup_tokens_two)
            )

        html = (APP / "static" / "index.html").read_text(encoding="utf-8")
        javascript = (APP / "static" / "app.js").read_text(encoding="utf-8")
        server_source = (APP / "server.py").read_text(encoding="utf-8")
        checks["frontend_component_present"] = all(
            marker in html
            for marker in [
                "owner-security-card",
                "generate_owner_token_btn",
                "owner_token_once_panel",
                "copy_owner_token_btn",
                "save_owner_token_note_btn",
                "generate_backup_tokens_btn",
                "generated_backup_tokens",
                "recover_owner_token_btn",
            ]
        )
        checks["frontend_uses_backend_generator"] = (
            'postJson("/api/security/owner-token/generate"' in javascript
            and 'fetch("/api/security/owner-token/status"' in javascript
            and 'postJson("/api/security/backup-tokens/generate"' in javascript
            and 'postJson("/api/security/backup-tokens/recover"' in javascript
            and "showGeneratedBackupTokens(" in javascript
            and "initialBackupTokens.length === 10" in javascript
        )
        checks["frontend_does_not_persist_owner_token"] = (
            "localStorage" not in javascript
            and "sessionStorage" not in javascript
        )
        checks["local_computer_gate_present"] = (
            "is_local_computer_address" in server_source
            and "allow_initial_setup=self.is_local_computer_request()" in server_source
        )
        checks["recovery_file_download_present"] = (
            "Download Private Recovery File" in html
            and 'link.download = "bbtc-owner-backup-tokens-private.txt"' in javascript
        )
    except Exception as error:
        errors.append(f"{type(error).__name__}: {error}")
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=5)

    failed = [name for name, passed in checks.items() if not passed]
    errors.extend(f"check_failed:{name}" for name in failed)
    report = {
        "version": VERSION,
        "status": "pass" if not errors else "fail",
        "checks": checks,
        "errors": errors,
        "non_claims": [
            "Validation reset only the temporary app copy to first-run state; repository settings were not changed.",
            "Generated token values are intentionally omitted from this report.",
            "This is local application security validation, not a security certification.",
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

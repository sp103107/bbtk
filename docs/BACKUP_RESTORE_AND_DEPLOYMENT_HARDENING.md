# Backup Restore and Deployment Operator Hardening — v0.5.0

## Mission

This phase adds verifiable backup archives, restore dry-run proof, and deployment preflight checks before the capsule moves toward a frozen release candidate.

## Backup model

Backups are ZIP archives generated from `repo_scaffold/app/data/`, excluding live backup and restore-candidate folders. Every backup includes `backup_manifest.json` with file hashes, data tree hash, source ledger hash, and restore policy.

## Restore model

Restore verification has two levels:

1. `verify_runtime_backup()` validates ZIP structure, manifest presence, file hashes, file count, and data tree hash.
2. `restore_dry_run()` extracts into `data/restore_candidates/` or a supplied candidate target and writes `restore_dry_run_receipt.json`.

The web route `/api/owner/backup/verify` performs verification plus dry-run extraction. It does **not** overwrite production data.

## Deployment preflight

Run:

```bash
python scripts/deployment_preflight.py
```

The preflight checks Python parseability, database initialization, writable data folders, owner-token setup warnings, PIN pepper warnings, loopback binding posture, and port availability.

## Required operator sequence before live use

```bash
python scripts/validate_repo.py
python scripts/runtime_smoke.py
python scripts/deployment_preflight.py
python repo_scaffold/app/server.py --host 127.0.0.1 --port 8080
```

Before real use, change:

- `owner_token`
- `pin_pepper`
- employee seed PINs

## Non-claims

- No production restore was performed.
- No production deployment was performed.
- No legal/payroll compliance seal is claimed.
- No AoS Boot Pod install, QEMU pass, rootfs materialization, or systemd activation is claimed.

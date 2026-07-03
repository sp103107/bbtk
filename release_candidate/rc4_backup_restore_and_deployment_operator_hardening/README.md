# RC4 — Backup Restore and Deployment Operator Hardening

## Version

`0.5.0`

## Objective

Convert backup creation from a loose archive action into a manifest-backed, verifiable backup and restore dry-run lane. Add deployment preflight checks for operator readiness.

## Acceptance evidence

- `scripts/runtime_smoke.py` proves backup creation, backup verification, and restore dry-run extraction in a temporary app copy.
- `scripts/deployment_preflight.py` writes `reports/deployment_preflight_report.v0.5.0.json`.
- `scripts/restore_runtime_data.py` supports operator dry-run restore and explicit apply mode.

## Non-claims

- No production restore was performed.
- No production deployment was performed.
- No legal/payroll compliance seal is claimed.

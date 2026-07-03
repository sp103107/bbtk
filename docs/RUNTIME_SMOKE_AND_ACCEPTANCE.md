# Runtime Smoke and Acceptance v0.2.0

## Acceptance posture

v0.2.0 is accepted only as a local standalone runtime scaffold if these commands pass:

```bash
python scripts/validate_repo.py
python scripts/runtime_smoke.py
```

## What the smoke proves

- temporary app copy initializes SQLite
- seed employee can clock in/out
- bad PIN is rejected
- summary calculation executes
- CSV export is generated
- employee upsert endpoint logic executes through runtime function calls

## What the smoke does not prove

- real production deployment
- legal compliance
- payroll correctness for every edge case
- user identity beyond PIN possession
- network/HTTPS security
- backup restore success

## Ledger verification

After live usage, run:

```bash
python scripts/verify_ledger.py --data-dir repo_scaffold/app/data --output reports/ledger_verify_report.local.json
```


## v0.5.0 backup/restore deployment hardening

Run `python scripts/runtime_smoke.py` to prove backup creation, backup verification, and restore dry-run extraction in a temporary app copy. Run `python scripts/deployment_preflight.py` before live use. Do not claim production deployment or production restore from these checks.

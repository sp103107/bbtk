# Owner Operator Runbook v0.2.0

## Start

```bash
python repo_scaffold/app/server.py --host 127.0.0.1 --port 8080
```

Open:

```text
http://127.0.0.1:8080
```

## Add employee

1. Enter owner token.
2. Fill employee ID, display name, and PIN.
3. Press **Save Employee**.
4. Press **List Employees** to confirm.

## Generate payroll export

1. Enter owner token.
2. Select date range.
3. Select export format.
4. Press **Generate Export**.
5. Use the generated download link.

## Backup data

Press **Backup Data** from the owner dashboard or run:

```bash
python scripts/backup_runtime_data.py --data-dir repo_scaffold/app/data --output-dir runtime_backups
```

## Audit check

```bash
python scripts/verify_ledger.py --data-dir repo_scaffold/app/data
```


## v0.5.0 backup/restore deployment hardening

Run `python scripts/runtime_smoke.py` to prove backup creation, backup verification, and restore dry-run extraction in a temporary app copy. Run `python scripts/deployment_preflight.py` before live use. Do not claim production deployment or production restore from these checks.

# Worker / Frontend Code Compliance — v0.8.1

## Rules

- Do not persist employee PINs in browser storage.
- Keep offline queue deterministic and inspectable.
- Render clear local receipts when backend is interrupted.
- Keep technical JSON hidden unless operator expands it.
- Preserve owner review before payroll-counting offline recovery records.

## Frontend files

- `repo_scaffold/app/static/offline_queue.js` handles local recovery queue and emergency downloads.
- `repo_scaffold/app/static/app.js` handles UI receipt rendering, sync calls, and status updates.

## Backend files

- `repo_scaffold/app/server.py` exposes `/api/offline/sync` and writes offline recovery records to JSONL with pending-owner-review status.

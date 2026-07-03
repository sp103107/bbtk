# Owner Payroll Close Runbook — v0.3.0

## Start the runtime

```bash
cd repo_scaffold/app
python server.py --host 127.0.0.1 --port 8080
```

Open:

```text
http://127.0.0.1:8080/
```

## Close a pay period

1. Enter the owner token.
2. Select Start and End dates.
3. Add an optional close note.
4. Click **Close Pay Period**.
5. Download the closed pay-period ZIP.
6. Review `owner_review.md`, `payroll_summary.csv`, and `exceptions.json` before using totals.

## Important boundary

The close operation freezes a review package from accepted events available at the close time. It does not prove payroll legality, cannabis compliance, or identity proof.

# Cursor Kickoff — Best Buds Time Clock Capsule v0.8.6

## First command

```bash
python scripts/onboard_agent.py
```

## Local dev start-all

Windows:

```bat
scripts\start_all.bat
```

## Employee portal

```text
http://COMPUTER-IP:8080/employee
```

## Current state

- Package: `best_buds_timeclock_capsule`
- Current version: `0.8.6`
- Current phase: `rc7_6_employee_qr_entry_and_kiosk_fit`
- Next phase: `rc7_7_owner_employee_admin_clarity`

## Required reads

```text
README.md
VERSION
CHANGELOG.md
repo_release_state.json
docs/EMPLOYEE_QR_ENTRY_PORTAL_v0.8.6.md
repo_scaffold/app/static/employee.html
repo_scaffold/app/static/employee.js
release_candidate/rc7_6_employee_qr_entry_and_kiosk_fit/
```

## Validation

```bash
python scripts/validate_employee_qr_entry.py
python scripts/validate_dev_startup_scripts.py
python scripts/validate_repo.py
python scripts/runtime_smoke.py
```

## Non-claims

- No production deployment.
- Employee QR/link is LAN entry helper only.
- PIN is still required after opening the employee portal.

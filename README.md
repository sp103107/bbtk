# Best Buds Time Clock Capsule v0.9.0

Standalone AoS-shaped QR/URL/kiosk time clock app for Best Buds Cannabis Cultivation — West Warwick, RI.

## Current bump

- Previous version: `0.8.6`
- Current version: `0.9.0`
- Arc: `arc_employee_management_kiosk_timeclock`
- Internal phase: `rc8_validation_and_context_checkpoint`
- Next internal phase: `arc_role_based_manager_permissions`
- Scope: Manager employee lifecycle, soft removal, kiosk guest visits, separate guest CSV, human-readable employee CSV, repaired manager buttons, and server-authoritative active-session polling.

## Short Windows path guidance

```text
C:\bbtc\bbtc_v0_8_6
```

## Entrypoints

`repo_scaffold/app/config/settings.json` and `repo_scaffold/app/data/` are local runtime state and are intentionally excluded from Git. A fresh clone starts from the safe built-in defaults; generate the owner token from the local operator console before real use.

Developer/Cursor agent onboarding:

```bash
python scripts/onboard_agent.py
```

Product user/operator start here:

```bash
python scripts/start_here_user.py
```

Guided + live-verifying onboarding (human or LLM agent):

```bash
python scripts/onboard_bbtc.py            # interactive human walkthrough + live check
python scripts/onboard_bbtc.py --json     # machine-readable JSON for an LLM agent
python scripts/onboard_bbtc.py --no-live  # informational only, no live server check
```

See `docs/ONBOARDING_PROGRAM.md` for details.

Local dev start-all (Windows):

```bat
scripts\start_all.bat
```

Start the local backend manually:

```bash
python -m pip install -r requirements.txt
python scripts/start_kiosk_server.py --host 0.0.0.0 --port 8080
```

Employee portal after backend is running:

```text
http://COMPUTER-IP:8080/employee
```

## Primary validation commands

```bash
python scripts/validate_employee_qr_entry.py
python scripts/validate_dev_startup_scripts.py
python scripts/validate_agent_onboarding_entrypoint.py
python scripts/validate_product_user_entrypoint.py
python scripts/validate_frontend_flow_status_language.py
python scripts/validate_repo.py
python scripts/runtime_smoke.py
```

## v0.9.0 manager, kiosk, guest, and live status arc

- Manager dashboard with selected-range summary and currently clocked-in employees.
- Employee create/update, deactivate, restore, and soft removal.
- Optional hourly rate and tax-estimate fields.
- Separate guest sign-in/out ledger and guest CSV export.
- Human-readable employee CSV with two-decimal hours and estimate columns.
- Summary and Manage Employees buttons target their correct panels.
- Active employees and guests share one owner live roster with separate counts.
- The owner can filter All/Employees/Guests, expand employee information, and clock out either person type from the onsite card.
- Reset Screen clears only browser state; Factory Reset is owner-authenticated, local-computer-only, phrase-gated, double-confirmed, and creates a verified backup before clearing runtime records.
- Authenticated WebSocket push updates the owner immediately; 15-second HTTP polling remains the fallback.
- The WebSocket listener uses the next local port (`8081` when HTTP uses `8080`).

## Preserved v0.8.6 employee QR entry

- Employee-only page at `/employee`
- Owner console **Employee Kiosk Link / QR** card
- `POST /api/employee/summary` for PIN-gated today-hours lookup
- `scripts/start_all.bat` and `scripts/start_all.sh` for local review

## Guided owner-token security

- The owner console can generate and atomically save a strong owner token.
- First-time setup is allowed only on the computer running BBTC, through loopback or its own LAN address.
- Initial setup creates the owner token and first 10 recovery tokens together.
- The recovery set can immediately be downloaded as a private file.
- Later rotation requires the current owner token.
- The configured token is never returned; a newly generated token is shown once.
- Owners can generate 10 single-use backup tokens; a new set invalidates the old set.
- Redeeming one backup token expires it and creates a new owner token.
- See `docs/OWNER_TOKEN_GENERATOR.md`.

## Non-claims

- No production deployment.
- No hosted public employee URL.
- No legal, payroll, or cannabis compliance seal.
- QR/link proves URL reachability only; PIN is still required.

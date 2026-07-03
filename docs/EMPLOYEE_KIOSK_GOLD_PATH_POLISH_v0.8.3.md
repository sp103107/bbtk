# Employee Kiosk Gold Path Polish v0.8.3

## Mission

Polish the employee-facing kiosk into a one-screen path: Employee ID, PIN, action, receipt, today-hours, and backend/offline state.

## What changed

- Added `.employee-focus-card` to tell the employee what to do now.
- Added `#employee_input_guard` so empty Employee ID/PIN attempts are blocked locally before backend or offline recovery.
- Added `.today-hours-card` so daily hours are visible outside technical JSON.
- Added `data-punch-action` to the four punch buttons for validator and future component targeting.
- Strengthened receipt and offline-pending copy.

## What this does not do

- It does not add payroll-provider integration.
- It does not make offline queue items payroll truth.
- It does not claim production deployment or legal compliance.
- It does not add the Hugging Face Space adapter.

## Validation

Run:

```bash
python scripts/validate_employee_kiosk_gold_path.py
python scripts/validate_repo.py
python scripts/runtime_smoke.py
```

## Next

Continue `rc7_4_owner_console_operator_clarity` to polish owner console operator clarity.

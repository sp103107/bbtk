# Frontend Flow Graphics Status Language — v0.8.5

## Purpose

This lane applies restrained flow/status graphics to the time clock UI. It uses small status rails to clarify sequence and state without turning the app into a busy cockpit.

## Employee flow

```text
ID → PIN → Punch → Receipt → Synced
```

The employee rail helps the worker understand where they are in the punch process.

## Owner flow

```text
Review → Export → Close → Backup → Verify
```

The owner rail supports the operator control panel without adding new backend scope.

## Offline recovery flow

```text
Backend Down → Local Queue → Sync Pending → Owner Review → Accepted/Rejected
```

Offline records remain recovery evidence only until synced and owner-reviewed.

## What changed

- added `employee_flow_rail`
- added `owner_flow_rail`
- added `offline_flow_rail`
- added CSS status states: active, done, pending, warning, error
- added JS helpers to mark flow state

## What this does not do

- does not add animation-heavy dashboards
- does not add a visual regression engine
- does not add backend routes
- does not claim production deployment
- does not claim payroll/legal/compliance certification

## Validation

```bash
python scripts/validate_frontend_flow_status_language.py
```

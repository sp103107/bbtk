# Current UI Surface Map v0.8.2

## Employee kiosk surface

The employee surface contains identity input, PIN input, clock actions, break actions, backend status, offline queue status, and receipt output.

Required visible states:

- ready
- backend checking
- backend online
- backend offline
- accepted punch
- rejected punch
- offline saved locally
- offline synced pending owner review

## Owner console surface

The owner console contains grouped task panels:

1. Today
2. Employees
3. Payroll Exports
4. Pay Period Close
5. Review / Adjustments
6. Offline Sync Review
7. Backup / Restore
8. Pilot / Release Readiness

## Technical diagnostics surface

Technical JSON and raw API responses must remain hidden behind disclosure blocks. They are operator diagnostics, not primary user experience.

## Non-claims

This map is static contract evidence only. It does not claim browser screenshot validation, visual regression execution, deployment, or production readiness.
